"""SEC 분기별 Financial Statement Data Sets 파서 (build+read, network 0).

URL 패턴: https://www.sec.gov/files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip
주기: 분기별, 분기말 +2~3개월에 공개. 크기: 60~130MB.

포함 파일: sub.txt, pre.txt, tag.txt, num.txt

⛔ 규칙: num.txt 는 받지 않는다.
수치값(val)의 원본은 companyfacts.zip 이다 (매일).
분기 벌크에서 필요한 것은 meta 정보만:
- sub.txt: adsh ↔ (cik, form, period, fy, fp, filed) 매핑
- pre.txt: adsh+tag → plabel/stmt/line/inpth (회사 표시명 + 계층)
- tag.txt: tag+version → tlabel/definition/datatype (태그 정의)

산출물:
    data/edgar/meta/sub/{Y}Q{Q}.parquet
    data/edgar/meta/pre/{Y}Q{Q}.parquet
    data/edgar/meta/tag/{Y}Q{Q}.parquet

NOTE: zip download(_headDataset/discoverLatestQuarter/downloadQuarterlyDataset)는
gather/edgar/datasetBulk 로 이관(수집 일원화) — 본 모듈은 zip→parquet 변환(build)과
로컬 분기 조회(read)만. zip 이 없으면 ``core.edgarClient.downloadQuarterlyDataset``
DIP 로 gather fetch 호출(providers↛gather 회피).
"""

from __future__ import annotations

import logging
import re
import zipfile
from io import BytesIO
from pathlib import Path

import polars as pl

_QUARTER_PARQUET_RE = re.compile(r"^(\d{4})Q([1-4])\.parquet$")

_log = logging.getLogger(__name__)

# num 은 받지 않는다 — companyfacts.zip 이 원본 (engines.edgar 원칙)
DATASET_FILES = ("sub", "pre", "tag")


# ── 경로 헬퍼 ─────────────────────────────────────────────────────────


def _metaDir(sub: str) -> Path:
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.core.dataLoader import _getDataRoot

    base = DATA_RELEASES.get("edgarMeta", {}).get("dir", "edgar/meta")
    d = _getDataRoot() / base / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


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
        df = df.with_columns(pl.col("filed").str.to_date("%Y%m%d", strict=False).alias("filed"))
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

    Raises:
        없음.

    Example:
        >>> convertQuarterlyToParquets(2024, 3)

    Args:
        year: int.
        quarter: int.
        zipPath: Path | None.

    Returns:
        dict[str, Path] — 결과.
    """
    if zipPath is None:
        # zip 부재 시 gather fetch 를 core DIP 로 호출(providers↛gather 회피).
        from dartlab.core.edgarClient import downloadQuarterlyDataset

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


def listLocalQuarters(*, kind: str = "sub", limit: int | None = None) -> list[tuple[int, int]]:
    """로컬 ``data/edgar/meta/{kind}/`` 에 있는 ``(year, quarter)`` 목록.

    Args:
        kind: SEC dataset 종류 (sub/num/pre/tag).
        limit: 최대 항목 수. None 이면 무제한.

    Returns:
        ``(year, quarter)`` 정렬 리스트.

    Raises:
        없음.

    Example:
        >>> listLocalQuarters(kind="sub", limit=8)
    """
    d = _metaDir(kind)
    out: list[tuple[int, int]] = []
    for p in d.glob("*.parquet"):
        m = _QUARTER_PARQUET_RE.match(p.name)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    out = sorted(out)
    if limit is not None:
        out = out[:limit]
    return out


def iterLocalQuarters(*, kind: str = "sub", limit: int | None = None):
    """``listLocalQuarters`` 의 iterator pair (룰 10).

    Args:
        kind: SEC dataset 종류 (sub/num/pre/tag).
        limit: 최대 항목 수. None 이면 무제한.

    Yields:
        ``(year, quarter)`` 튜플.

    Raises:
        없음.

    Example:
        >>> for y, q in iterLocalQuarters(limit=8):
        ...     print(y, q)
    """
    yield from listLocalQuarters(kind=kind, limit=limit)


__all__ = [
    "DATASET_FILES",
    "convertQuarterlyToParquets",
    "listLocalQuarters",
    "iterLocalQuarters",
]
