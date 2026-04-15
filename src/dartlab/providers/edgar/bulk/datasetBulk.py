"""SEC 분기별 Financial Statement Data Sets 벌크 다운로더·파서.

URL 패턴: https://www.sec.gov/files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip
주기: 분기별, 분기말 +2~3개월에 공개
크기: 60~130MB

포함 파일: sub.txt, pre.txt, tag.txt, num.txt

⛔ 규칙: num.txt 는 받지 않는다.
수치값(val)의 원본은 `companyfactsBulk.py` 가 매일 받는 companyfacts.zip 이다.
분기 벌크에서 필요한 것은 meta 정보만:
- sub.txt: adsh ↔ (cik, form, period, fy, fp, filed) 매핑
- pre.txt: adsh+tag → plabel/stmt/line/inpth (회사 표시명 + 계층)
- tag.txt: tag+version → tlabel/definition/datatype (태그 정의)

산출물:
    data/edgar/meta/sub/{Y}Q{Q}.parquet
    data/edgar/meta/pre/{Y}Q{Q}.parquet
    data/edgar/meta/tag/{Y}Q{Q}.parquet
"""

from __future__ import annotations

import logging
import re
import zipfile
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path

import httpx
import polars as pl

from dartlab.providers.edgar.bulk.freshness import (
    isBulkFresh,
    readSavedEtag,
    touchBulkFreshness,
)

_log = logging.getLogger(__name__)

_BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
_LANDING_URL = (
    "https://www.sec.gov/data-research/sec-markets-data/"
    "financial-statement-data-sets"
)
_UA = "dartlab eddmpython@gmail.com"

_DEFAULT_TIMEOUT = httpx.Timeout(60.0, read=None, write=60.0, connect=30.0)

# num 은 받지 않는다 — companyfacts.zip 이 원본 (ops/edgar.md 원칙)
DATASET_FILES = ("sub", "pre", "tag")


# ── 경로 헬퍼 ─────────────────────────────────────────────────────────


def _bulkDir() -> Path:
    from dartlab import config as _cfg

    d = Path(_cfg.dataDir) / "edgar" / "_bulk" / "quarterly"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _metaDir(sub: str) -> Path:
    from dartlab import config as _cfg
    from dartlab.core.dataConfig import DATA_RELEASES

    base = DATA_RELEASES.get("edgarMeta", {}).get("dir", "edgar/meta")
    d = Path(_cfg.dataDir) / base / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def _quarterTag(year: int, quarter: int) -> str:
    return f"quarterly_{year}Q{quarter}"


def _datasetUrl(year: int, quarter: int) -> str:
    return f"{_BASE_URL}/{year}q{quarter}.zip"


# ── 다운로드 ─────────────────────────────────────────────────────────


def _headDataset(year: int, quarter: int) -> httpx.Response | None:
    """분기 zip 존재 여부 HEAD. 404 면 None, 200 이면 Response."""
    url = _datasetUrl(year, quarter)
    headers = {"User-Agent": _UA, "Accept-Encoding": "identity"}
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
            resp = client.head(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        _log.warning("dataset %sQ%s HEAD 실패: %s", year, quarter, exc)
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        _log.warning("dataset %sQ%s HEAD status=%s", year, quarter, resp.status_code)
        return None
    return resp


def discoverLatestQuarter(maxYear: int | None = None) -> tuple[int, int] | None:
    """SEC 에 공개된 최신 분기를 HEAD 요청으로 탐색.

    maxYear=None 이면 현재 연도까지 체크. 공개된 (year, quarter) 튜플 반환.
    분기말 +2~3개월 지연이 있으므로 일반적으로 현재 분기-1 이 최신.
    """
    if maxYear is None:
        maxYear = datetime.now(timezone.utc).year

    # 최신 → 과거 순으로 체크, 최초 200 응답에서 멈춤
    for year in range(maxYear, maxYear - 3, -1):
        for quarter in (4, 3, 2, 1):
            # 미래 분기는 건너뜀
            qEnd = date(year, quarter * 3, 1)
            if qEnd > date.today():
                continue
            resp = _headDataset(year, quarter)
            if resp is not None:
                return year, quarter
    return None


def downloadQuarterlyDataset(
    year: int,
    quarter: int,
    *,
    force: bool = False,
    ttlHours: int = 24 * 30,
) -> Path | None:
    """`{Y}q{Q}.zip` 다운로드. 존재하지 않으면 None.

    분기 벌크는 한 번 공개 후 변동이 적으므로 기본 TTL 30일.
    """
    tag = _quarterTag(year, quarter)
    zipPath = _bulkDir() / f"{year}q{quarter}.zip"

    if not force and zipPath.exists() and isBulkFresh(tag, ttlHours=ttlHours):
        return zipPath

    url = _datasetUrl(year, quarter)
    headers = {"User-Agent": _UA, "Accept-Encoding": "identity"}

    savedEtag = readSavedEtag(tag)
    with httpx.Client(timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
        try:
            head = client.head(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            _log.warning("dataset %sq%s HEAD 실패: %s", year, quarter, exc)
            return None
        if head.status_code == 404:
            return None
        if head.status_code >= 400:
            _log.warning(
                "dataset %sq%s status=%s — 스킵", year, quarter, head.status_code
            )
            return None

        remoteEtag = head.headers.get("ETag", "").strip('"')
        remoteLen = int(head.headers.get("Content-Length", "0") or 0)

        if (
            not force
            and savedEtag
            and remoteEtag
            and savedEtag == remoteEtag
            and zipPath.exists()
            and zipPath.stat().st_size == remoteLen
        ):
            touchBulkFreshness(tag, etag=remoteEtag)
            return zipPath

        _log.info(
            "dataset %sq%s 다운로드 (%.1f MB)", year, quarter, remoteLen / 1024 / 1024
        )
        tmpPath = zipPath.with_suffix(".zip.tmp")
        with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            with tmpPath.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        tmpPath.replace(zipPath)
        touchBulkFreshness(tag, etag=remoteEtag)
        return zipPath


# ── TSV 파싱 ──────────────────────────────────────────────────────────

# 공식 SEC 레코드 스펙 (financial-statement-data-sets/README)
# 모든 파일은 tab-separated, 첫 행이 컬럼명, 인코딩은 latin-1/cp1252 혼재
_SUB_DTYPES = {
    "adsh": pl.Utf8,
    "cik": pl.Utf8,
    "name": pl.Utf8,
    "form": pl.Utf8,
    "period": pl.Utf8,
    "fy": pl.Int32,
    "fp": pl.Utf8,
    "filed": pl.Utf8,
    "accepted": pl.Utf8,
    "instance": pl.Utf8,
    "countryba": pl.Utf8,
    "stprba": pl.Utf8,
    "cityba": pl.Utf8,
    "sic": pl.Utf8,
    "ein": pl.Utf8,
    "fye": pl.Utf8,
    "detail": pl.Int32,
    "nbr": pl.Int32,
}

_PRE_DTYPES = {
    "adsh": pl.Utf8,
    "report": pl.Int32,
    "line": pl.Int32,
    "stmt": pl.Utf8,
    "inpth": pl.Int32,
    "rfile": pl.Utf8,
    "tag": pl.Utf8,
    "version": pl.Utf8,
    "plabel": pl.Utf8,
    "negating": pl.Int32,
}

_TAG_DTYPES = {
    "tag": pl.Utf8,
    "version": pl.Utf8,
    "custom": pl.Int32,
    "abstract": pl.Int32,
    "datatype": pl.Utf8,
    "iord": pl.Utf8,
    "crdr": pl.Utf8,
    "tlabel": pl.Utf8,
    "doc": pl.Utf8,
}


def _readTsvFromZip(
    zipPath: Path,
    member: str,
    dtypes: dict[str, pl.DataType],
) -> pl.DataFrame:
    """분기 zip 에서 sub/pre/tag.txt 읽어서 DataFrame 으로.

    SEC TSV 는 latin-1 인코딩, tab 구분. 일부 행에 따옴표/백슬래시 이상값 있어서
    polars `read_csv` 의 관용 모드로 처리.
    """
    with zipfile.ZipFile(zipPath, "r") as zf:
        try:
            raw = zf.read(member)
        except KeyError:
            return pl.DataFrame(schema=dtypes)

    # SEC TSV 는 latin-1. polars 는 UTF-8 만 받으므로 재인코딩.
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="replace")
    buf = BytesIO(text.encode("utf-8"))

    try:
        df = pl.read_csv(
            buf,
            separator="\t",
            has_header=True,
            infer_schema_length=0,
            null_values=["", "NA", "NULL"],
            truncate_ragged_lines=True,
            quote_char=None,
        )
    except pl.exceptions.PolarsError as exc:
        _log.warning("TSV %s 파싱 실패: %s", member, exc)
        return pl.DataFrame(schema=dtypes)

    # 타입 캐스팅 (best-effort)
    casts = []
    for col, dtype in dtypes.items():
        if col in df.columns:
            casts.append(pl.col(col).cast(dtype, strict=False))
    if casts:
        df = df.with_columns(casts)

    # 지정되지 않은 컬럼도 보존, 단 dtypes 에 없는 건 문자열 그대로
    return df


def _parseSub(zipPath: Path) -> pl.DataFrame:
    df = _readTsvFromZip(zipPath, "sub.txt", _SUB_DTYPES)
    if df.height == 0:
        return df
    if "cik" in df.columns:
        df = df.with_columns(pl.col("cik").str.zfill(10).alias("cik"))
    if "filed" in df.columns:
        # YYYYMMDD 문자열 → date (strict=False, 실패시 null)
        df = df.with_columns(
            pl.col("filed").str.to_date("%Y%m%d", strict=False).alias("filed")
        )
    return df


def _parsePre(zipPath: Path) -> pl.DataFrame:
    df = _readTsvFromZip(zipPath, "pre.txt", _PRE_DTYPES)
    return df


def _parseTag(zipPath: Path) -> pl.DataFrame:
    df = _readTsvFromZip(zipPath, "tag.txt", _TAG_DTYPES)
    return df


def convertQuarterlyToParquets(
    year: int,
    quarter: int,
    *,
    zipPath: Path | None = None,
) -> dict[str, Path]:
    """분기 zip → data/edgar/meta/{sub,pre,tag}/{Y}Q{Q}.parquet 저장.

    num 은 받지 않고 파싱도 하지 않는다 (원칙: companyfacts.zip 이 값 원본).

    Returns
    -------
    dict { "sub": Path, "pre": Path, "tag": Path }
    """
    if zipPath is None:
        zipPath = downloadQuarterlyDataset(year, quarter)
    if zipPath is None or not zipPath.exists():
        return {}

    outSuffix = f"{year}Q{quarter}.parquet"
    outPaths: dict[str, Path] = {}

    for name, parser in (("sub", _parseSub), ("pre", _parsePre), ("tag", _parseTag)):
        df = parser(zipPath)
        if df.height == 0:
            _log.warning("%sq%s %s.txt 비어있음", year, quarter, name)
            continue
        outPath = _metaDir(name) / outSuffix
        tmpPath = outPath.with_suffix(".parquet.tmp")
        df.write_parquet(tmpPath, compression="zstd")
        tmpPath.replace(outPath)
        outPaths[name] = outPath
        _log.info("meta/%s/%s: %d rows", name, outSuffix, df.height)

    return outPaths


def listLocalQuarters(*, kind: str = "sub") -> list[tuple[int, int]]:
    """로컬 `data/edgar/meta/{kind}/` 에 있는 (year, quarter) 목록."""
    d = _metaDir(kind)
    pattern = re.compile(r"^(\d{4})Q([1-4])\.parquet$")
    out: list[tuple[int, int]] = []
    for p in d.glob("*.parquet"):
        m = pattern.match(p.name)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return sorted(out)


__all__ = [
    "DATASET_FILES",
    "convertQuarterlyToParquets",
    "discoverLatestQuarter",
    "downloadQuarterlyDataset",
    "listLocalQuarters",
]
