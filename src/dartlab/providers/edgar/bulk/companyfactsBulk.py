"""SEC daily companyfacts.zip 벌크 다운로더·파서.

URL: https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip
주기: 매일 04:25 UTC, 크기 ~1.37GB
내용: 전체 상장사 XBRL facts가 `CIK{0padded10}.json` 파일들로 압축

파이프라인:
    downloadCompanyfactsBulk()  → data/edgar/_bulk/companyfacts.zip
    extractCompanyfactsZip()    → iter (cik, json_dict)
    convertBulkToParquets()     → data/edgar/finance/{cik}.parquet

기존 `openapi/facts.py::companyFactsToRows()` 를 그대로 재사용.
이 모듈은 zip 스트리밍과 일괄 변환만 책임진다.
"""

from __future__ import annotations

import json
import logging
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

import httpx
import polars as pl

from dartlab.providers.edgar.bulk.freshness import (
    isBulkFresh,
    readSavedEtag,
    touchBulkFreshness,
)
from dartlab.providers.edgar.openapi.facts import (
    EDGAR_COMPANYFACTS_SCHEMA,
    companyFactsToRows,
)

_log = logging.getLogger(__name__)

_BULK_URL = "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip"

# SEC fair access: User-Agent with contact required.
# https://www.sec.gov/os/accessing-edgar-data
_UA = "dartlab eddmpython@gmail.com"

_DEFAULT_TIMEOUT = httpx.Timeout(60.0, read=None, write=60.0, connect=30.0)


def _bulkDir() -> Path:
    from dartlab import config as _cfg

    d = Path(_cfg.dataDir) / "edgar" / "_bulk"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _financeDir() -> Path:
    from dartlab import config as _cfg
    from dartlab.core.dataConfig import DATA_RELEASES

    d = Path(_cfg.dataDir) / DATA_RELEASES["edgar"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def downloadCompanyfactsBulk(
    *,
    force: bool = False,
    ttlHours: int = 24,
    progress: bool = True,
) -> Path:
    """SEC companyfacts.zip 를 `data/edgar/_bulk/companyfacts.zip` 로 다운로드.

    HEAD 요청으로 원격 ETag + Last-Modified 확인 후 로컬 TTL/ETag와 비교.
    force=False (기본) 이면 TTL 내이고 ETag 일치하면 스킵.

    Parameters
    ----------
    force : bool
        True 면 로컬 파일 상태와 무관하게 재다운로드.
    ttlHours : int
        로컬 freshness TTL. SEC companyfacts 는 매일 04:25 UTC 갱신되므로 24h 기본.
    progress : bool
        tqdm 진행률 표시 (stderr).
    """
    zipPath = _bulkDir() / "companyfacts.zip"
    tag = "companyfacts"

    if not force and zipPath.exists() and isBulkFresh(tag, ttlHours=ttlHours):
        _log.info("companyfacts.zip fresh (TTL=%dh) — 다운로드 스킵", ttlHours)
        return zipPath

    headers = {"User-Agent": _UA, "Accept-Encoding": "identity"}

    # HEAD 로 ETag + Content-Length 확인 (네트워크 낭비 방지)
    savedEtag = readSavedEtag(tag)
    with httpx.Client(timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
        head = client.head(_BULK_URL, follow_redirects=True)
        head.raise_for_status()
        remoteEtag = head.headers.get("ETag", "").strip('"')
        remoteLen = int(head.headers.get("Content-Length", "0") or 0)
        remoteLastModified = head.headers.get("Last-Modified", "")

        if (
            not force
            and savedEtag
            and remoteEtag
            and savedEtag == remoteEtag
            and zipPath.exists()
            and zipPath.stat().st_size == remoteLen
        ):
            _log.info("companyfacts.zip ETag+Size 일치 — 다운로드 스킵 (%s)", remoteEtag)
            touchBulkFreshness(tag, etag=remoteEtag)
            return zipPath

        _log.info(
            "companyfacts.zip 다운로드 시작: %s (%.1f MB, Last-Modified=%s)",
            _BULK_URL,
            remoteLen / 1024 / 1024,
            remoteLastModified,
        )
        _emitStart(remoteLen)

        tmpPath = zipPath.with_suffix(".zip.tmp")
        with client.stream("GET", _BULK_URL, follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", "0") or 0) or remoteLen
            downloaded = 0
            chunk = 1024 * 1024  # 1MB
            bar = _initBar(total, show=progress)
            try:
                with tmpPath.open("wb") as f:
                    for data in resp.iter_bytes(chunk_size=chunk):
                        f.write(data)
                        downloaded += len(data)
                        if bar is not None:
                            bar.update(len(data))
            finally:
                if bar is not None:
                    bar.close()

        tmpPath.replace(zipPath)
        touchBulkFreshness(tag, etag=remoteEtag)
        _emitDone(zipPath, downloaded)
        return zipPath


def extractCompanyfactsZip(zipPath: Path) -> Iterator[tuple[str, dict]]:
    """companyfacts.zip 스트리밍 해제 → (cik, json_dict) yield.

    zip 안의 파일명은 `CIK{10자리}.json` 형식. cik 는 0-padded 10자리 문자열로
    반환된다. 손상된 JSON 항목은 로깅 후 건너뛴다.
    """
    with zipfile.ZipFile(zipPath, "r") as zf:
        for info in zf.infolist():
            name = info.filename
            if not name.endswith(".json"):
                continue
            stem = Path(name).stem
            cik = stem.replace("CIK", "").lstrip("0") or "0"
            cikPadded = cik.zfill(10)
            try:
                with zf.open(info) as f:
                    payload = json.load(f)
            except (json.JSONDecodeError, zipfile.BadZipFile, OSError) as exc:
                _log.warning("zip entry %s 파싱 실패: %s", name, exc)
                continue
            yield cikPadded, payload


def convertBulkToParquets(
    zipPath: Path | None = None,
    *,
    outDir: Path | None = None,
    onlyCiks: set[str] | None = None,
    progress: bool = True,
) -> dict[str, int]:
    """companyfacts.zip → `data/edgar/finance/{cik}.parquet` 일괄 생성.

    Parameters
    ----------
    zipPath : Path | None
        None 이면 `data/edgar/_bulk/companyfacts.zip` 사용. 없으면 자동 다운로드.
    outDir : Path | None
        None 이면 DATA_RELEASES["edgar"]["dir"] (`data/edgar/finance`).
    onlyCiks : set[str] | None
        지정된 cik(0-padded 10자리)만 변환. 테스트/샘플용.
    progress : bool
        tqdm 진행률.

    Returns
    -------
    dict {"converted": N, "skipped": M, "failed": K}
    """
    if zipPath is None:
        zipPath = downloadCompanyfactsBulk(progress=progress)
    if not zipPath.exists():
        raise FileNotFoundError(zipPath)

    target = outDir or _financeDir()
    target.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0
    failed = 0

    with zipfile.ZipFile(zipPath, "r") as zf:
        entries = [i for i in zf.infolist() if i.filename.endswith(".json")]

    bar = _initBar(len(entries), show=progress, unit="files")

    try:
        for cik, payload in extractCompanyfactsZip(zipPath):
            if onlyCiks is not None and cik not in onlyCiks:
                skipped += 1
                if bar is not None:
                    bar.update(1)
                continue
            try:
                df = companyFactsToRows(payload)
                if df.height == 0:
                    skipped += 1
                else:
                    outPath = target / f"{cik}.parquet"
                    tmpPath = outPath.with_suffix(".parquet.tmp")
                    df.write_parquet(tmpPath, compression="zstd")
                    tmpPath.replace(outPath)
                    converted += 1
            except (
                ValueError,
                TypeError,
                OSError,
                pl.exceptions.PolarsError,
            ) as exc:
                failed += 1
                _log.warning("CIK %s 변환 실패: %s", cik, exc)
            if bar is not None:
                bar.update(1)
    finally:
        if bar is not None:
            bar.close()

    # 변환 완료 시각 기록 (다운스트림 스크립트 용)
    stamp = _bulkDir() / "companyfacts.converted"
    stamp.write_text(
        datetime.now(timezone.utc).isoformat(timespec="seconds"), encoding="utf-8"
    )

    _log.info(
        "companyfacts.zip → parquet 변환 완료: converted=%d skipped=%d failed=%d",
        converted,
        skipped,
        failed,
    )
    return {"converted": converted, "skipped": skipped, "failed": failed}


# ── 진행률/이벤트 헬퍼 ─────────────────────────────────────────────────


def _initBar(total: int, *, show: bool, unit: str = "B"):
    """tqdm 진행률 바 생성. tqdm 없으면 None."""
    if not show or total <= 0:
        return None
    try:
        from tqdm import tqdm
    except ImportError:
        return None
    unit_scale = unit == "B"
    return tqdm(
        total=total,
        unit=unit,
        unit_scale=unit_scale,
        unit_divisor=1024 if unit_scale else 1000,
        desc="companyfacts.zip",
    )


def _emitStart(totalBytes: int) -> None:
    """companyfacts.zip 다운로드 시작 안내 — guide.emit 으로 [dartlab] 출력."""
    try:
        from dartlab.guide.messaging import emit

        emit("edgar:bulk_download_start")
    except ImportError:
        pass
    _log.info("companyfacts.zip 다운로드 시작 — %.1f MB", totalBytes / 1024 / 1024)


def _emitDone(zipPath: Path, downloaded: int, *, elapsedSec: float = 0.0) -> None:
    """다운로드 완료 안내."""
    try:
        from dartlab.guide.messaging import emit

        emit(
            "edgar:bulk_download_done",
            sizeMB=downloaded / 1024 / 1024,
            elapsedSec=elapsedSec,
        )
    except ImportError:
        pass
    _log.info(
        "companyfacts.zip 다운로드 완료 — %s (%.1f MB)",
        zipPath,
        downloaded / 1024 / 1024,
    )


def _emitFresh(ttlHours: int) -> None:
    try:
        from dartlab.guide.messaging import emit

        emit("edgar:bulk_fresh", ttlHours=ttlHours)
    except ImportError:
        pass


def _emitConvertStart(totalCiks: int) -> None:
    try:
        from dartlab.guide.messaging import emit

        emit("edgar:bulk_convert_start", totalCiks=totalCiks)
    except ImportError:
        pass


def _emitConvertDone(
    *, converted: int, skipped: int, failed: int, elapsedSec: float
) -> None:
    try:
        from dartlab.guide.messaging import emit

        emit(
            "edgar:bulk_convert_done",
            converted=converted,
            skipped=skipped,
            failed=failed,
            elapsedSec=elapsedSec,
        )
    except ImportError:
        pass


__all__ = [
    "EDGAR_COMPANYFACTS_SCHEMA",
    "convertBulkToParquets",
    "downloadCompanyfactsBulk",
    "extractCompanyfactsZip",
]
