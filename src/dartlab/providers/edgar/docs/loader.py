"""EDGAR docs parquet 로더 — 로컬 캐시 보장·증분·재구축.

핵심 함수:

- ``ensureEdgarDocs(stockCode, path, *, sinceYear, asOf, refresh)`` — 로컬 docs
  parquet 을 보장 (없으면 HF 다운로드 또는 SEC API 재구축, refresh 정책에
  따라 신선도 체크 + 증분 갱신).
- ``getLatestRegularEdgarFiling`` / ``getLocalEdgarDocsState`` /
  ``isEdgarDocsFresh`` — 신선도 비교 helpers.
- ``rebuildEdgarDocs`` — SEC API 로 전체 재구축.
- ``incrementalUpdateEdgarDocs`` — 신규 filing 만 증분 추가.

옛 위치: ``core/dataLoader.py`` (Cut 7-step2 에서 EDGAR 도메인 코드 분리).
"""

from __future__ import annotations

import inspect
import sys
import time
from pathlib import Path
from typing import Any

import polars as pl

_IS_PYODIDE = sys.platform == "emscripten"

if not _IS_PYODIDE:
    import socket
    from urllib.error import URLError

EDGAR_DOCS_FRESHNESS_TTL_HOURS = 24


def ensureEdgarDocs(
    stockCode: str,
    path: Path,
    *,
    sinceYear: int,
    asOf: str | None,
    refresh: str,
) -> None:
    """로컬 EDGAR docs parquet 을 보장.

    refresh 정책:
    - ``local_only`` — 로컬 없으면 ``FileNotFoundError``.
    - ``force_rebuild`` — SEC API 로 전체 재구축.
    - ``force_check``/``auto`` — 로컬 있으면 신선도 비교 후 필요시 증분.

    Args:
        stockCode: 종목 ticker.
        path: 로컬 parquet 경로.
        sinceYear: 시작 연도.
        asOf: 신선도 기준 시점 (None 이면 latest 기준).
        refresh: ``auto``/``force_check``/``force_rebuild``/``local_only``.

    Raises:
        ValueError: 미지원 refresh 정책.
        FileNotFoundError: ``local_only`` + 로컬 부재.

    Example:
        >>> ensureEdgarDocs("AAPL", Path("data/edgar/docs/AAPL.parquet"), sinceYear=2009, asOf=None, refresh="auto")
    """
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.core.dataLoader import _download
    from dartlab.core.messaging import emit

    if refresh not in {"auto", "force_check", "force_rebuild", "local_only"}:
        raise ValueError(f"지원하지 않는 refresh 정책: {refresh}")

    if refresh == "local_only":
        if not path.exists():
            raise FileNotFoundError(f"로컬 EDGAR docs 없음: {path}")
        return

    if refresh == "force_rebuild":
        rebuildEdgarDocs(stockCode, path, sinceYear=sinceYear, sourceMode="sec_api_rebuild")
        return

    if not path.exists():
        label = DATA_RELEASES["edgarDocs"]["label"]
        emit("download:start", stockCode=stockCode, label=label)
        try:
            _download(stockCode, path, "edgarDocs")
            size = path.stat().st_size
            sizeStr = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
            emit("download:done_short", sizeStr=sizeStr)
        except (URLError, socket.timeout, OSError):
            if path.exists():
                path.unlink()
            emit("edgar:fallback")
            rebuildEdgarDocs(stockCode, path, sinceYear=sinceYear, sourceMode="sec_api")
        return

    if refresh == "auto" and not isEdgarDocsCheckExpired(path):
        return

    latestRemote = getLatestRegularEdgarFiling(stockCode, sinceYear=sinceYear)
    if latestRemote is None:
        return
    localState = getLocalEdgarDocsState(path)
    if localState is not None and isEdgarDocsFresh(localState, latestRemote, asOf=asOf):
        return
    incrementalUpdateEdgarDocs(stockCode, path, sinceYear=sinceYear, latestRemote=latestRemote)


def isEdgarDocsCheckExpired(path: Path) -> bool:
    """로컬 docs parquet 의 신선도 체크 TTL 만료 여부.

    Args:
        path: 로컬 parquet 경로.

    Returns:
        ``True`` — 24h TTL 만료 또는 파일 부재. ``False`` — 아직 신선.

    Raises:
        없음.

    Example:
        >>> isEdgarDocsCheckExpired(Path("data/edgar/docs/AAPL.parquet"))
    """
    if not path.exists():
        return True
    ageSeconds = time.time() - path.stat().st_mtime
    return ageSeconds > EDGAR_DOCS_FRESHNESS_TTL_HOURS * 3600


def getLatestRegularEdgarFiling(stockCode: str, *, sinceYear: int) -> dict[str, str] | None:
    """SEC submissions API 에서 최신 정기 공시 1 건 메타 반환.

    Args:
        stockCode: 종목 ticker.
        sinceYear: 시작 연도.

    Returns:
        ``ticker/cik/filing_date/accession_no/form_type`` dict 또는 None (filing 부재).

    Raises:
        httpx.HTTPError: SEC API 호출 실패.

    Example:
        >>> getLatestRegularEdgarFiling("AAPL", sinceYear=2024)
    """
    from dartlab.providers.edgar.docs.fetch import _findFilings, _getSubmissions, _resolveTickerMeta

    meta = _resolveTickerMeta(stockCode.upper())
    submissions = _getSubmissions(meta["cik"])
    filings = _findFilings(submissions, sinceYear)
    if not filings:
        return None
    latest = filings[-1]
    return {
        "ticker": stockCode.upper(),
        "cik": meta["cik"],
        "filing_date": latest["filingDate"],
        "accession_no": latest["accessionNumber"],
        "form_type": latest["formType"],
    }


def getLocalEdgarDocsState(path: Path) -> dict[str, str] | None:
    """로컬 docs parquet 의 최신 filing 상태 (날짜·accession).

    Args:
        path: 로컬 parquet 경로.

    Returns:
        ``latest_filing_date``/``latest_accession_no`` dict 또는 None.

    Raises:
        없음.

    Example:
        >>> getLocalEdgarDocsState(Path("data/edgar/docs/AAPL.parquet"))
    """
    if not path.exists():
        return None
    df = pl.read_parquet(path, columns=["filing_date", "accession_no"])
    if df.is_empty():
        return None
    latestDate = df["filing_date"].drop_nulls().max()
    latestAccession = ""
    if latestDate is not None:
        latestRows = df.filter(pl.col("filing_date") == latestDate)
        if latestRows.height and "accession_no" in latestRows.columns:
            latestAccession = str(latestRows["accession_no"][0] or "")
    return {
        "latest_filing_date": str(latestDate or ""),
        "latest_accession_no": latestAccession,
    }


def isEdgarDocsFresh(localState: dict[str, str], latestRemote: dict[str, str], *, asOf: str | None) -> bool:
    """로컬 상태 vs 원격 최신 비교.

    Args:
        localState: ``getLocalEdgarDocsState`` 결과.
        latestRemote: ``getLatestRegularEdgarFiling`` 결과.
        asOf: 신선도 기준 시점 (None 이면 latest 비교).

    Returns:
        ``True`` — 로컬이 원격과 동등 이상.

    Raises:
        없음.

    Example:
        >>> isEdgarDocsFresh(local, remote, asOf=None)
    """
    latestAccession = str(localState.get("latest_accession_no") or "")
    latestDate = str(localState.get("latest_filing_date") or "")
    if asOf is not None and latestDate:
        return latestDate >= asOf
    if latestDate and latestDate > latestRemote["filing_date"]:
        return True
    if latestDate and latestDate == latestRemote["filing_date"]:
        return latestAccession == latestRemote["accession_no"] or bool(latestAccession)
    if latestAccession:
        return latestAccession == latestRemote["accession_no"]
    return latestDate == latestRemote["filing_date"]


def _callFetchEdgarDocs(
    fetchFn: Any,
    stockCode: str,
    path: Path,
    *,
    sinceYear: int,
    sourceMode: str,
) -> None:
    """fetchEdgarDocs 호출 어댑터 — 시그니처 진화 흡수."""
    kwargs: dict[str, Any] = {"sinceYear": sinceYear}
    try:
        signature = inspect.signature(fetchFn)
    except (TypeError, ValueError):
        signature = None

    if signature is None or "sourceMode" in signature.parameters:
        kwargs["sourceMode"] = sourceMode
    if signature is None or "strictQuality" in signature.parameters:
        kwargs["strictQuality"] = False

    fetchFn(stockCode, path, **kwargs)


def rebuildEdgarDocs(stockCode: str, path: Path, *, sinceYear: int, sourceMode: str) -> None:
    """SEC API 로 docs parquet 전체 재구축.

    Args:
        stockCode: 종목 ticker.
        path: 저장 경로.
        sinceYear: 시작 연도.
        sourceMode: fetch source mode (예: ``"sec_api"``).

    Raises:
        URLError: SEC API 다운로드 실패.
        OSError: 파일 쓰기 실패.
        ValueError: filing 부재.

    Example:
        >>> rebuildEdgarDocs("AAPL", Path("data/edgar/docs/AAPL.parquet"), sinceYear=2009, sourceMode="sec_api")
    """
    from dartlab.providers.edgar.docs.fetch import fetchEdgarDocs

    try:
        _callFetchEdgarDocs(
            fetchEdgarDocs,
            stockCode,
            path,
            sinceYear=sinceYear,
            sourceMode=sourceMode,
        )
    except (URLError, OSError, ValueError):
        if path.exists():
            path.unlink()
        raise


def incrementalUpdateEdgarDocs(
    stockCode: str,
    path: Path,
    *,
    sinceYear: int,
    latestRemote: dict[str, str],
) -> None:
    """신규 filing 만 SEC API 로 가져와 기존 parquet 에 append.

    Args:
        stockCode: 종목 ticker.
        path: 기존 parquet 경로.
        sinceYear: 시작 연도.
        latestRemote: 원격 최신 filing 메타.

    Raises:
        httpx.HTTPError: SEC API 호출 실패.
        OSError: 파일 쓰기 실패.

    Example:
        >>> incrementalUpdateEdgarDocs("AAPL", Path("..."), sinceYear=2009, latestRemote=remote)
    """
    from dartlab.core.messaging import emit
    from dartlab.providers.edgar.docs.fetch import (
        FILING_TIMEOUT_SECONDS,
        _collectFilingRows,
        _findFilings,
        _getSubmissions,
        _makeProgress,
        _resolveTickerMeta,
    )

    currentDf = pl.read_parquet(path)
    existingAccessions = (
        set(currentDf["accession_no"].drop_nulls().to_list()) if "accession_no" in currentDf.columns else set()
    )
    meta = _resolveTickerMeta(stockCode.upper())
    filings = _findFilings(_getSubmissions(meta["cik"]), sinceYear)
    newFilings = [filing for filing in filings if filing["accessionNumber"] not in existingAccessions]
    if not newFilings:
        emit("edgar:no_new", ticker=stockCode.upper())
        return

    emit("edgar:incremental_start", ticker=stockCode.upper(), newCount=len(newFilings))

    rows: list[dict] = []
    skipped: list[str] = []
    _prog, _bar = _makeProgress(len(newFilings), f"EDGAR 증분 | {stockCode.upper()}")
    with _prog:
        _collectFilingRows(rows, newFilings, meta, stockCode.upper(), _bar, FILING_TIMEOUT_SECONDS, skipped)

    if not rows:
        return
    newDf = pl.DataFrame(rows)

    # 스키마 정합: currentDf 컬럼 기준으로 newDf 정렬 + 누락 컬럼 NULL 추가
    for col in currentDf.columns:
        if col not in newDf.columns:
            newDf = newDf.with_columns(pl.lit(None).cast(currentDf.schema[col]).alias(col))
    for col in newDf.columns:
        if col not in currentDf.columns:
            currentDf = currentDf.with_columns(pl.lit(None).cast(newDf.schema[col]).alias(col))
    # 타입 통일
    for col in currentDf.columns:
        if col in newDf.columns and currentDf.schema[col] != newDf.schema[col]:
            try:
                newDf = newDf.with_columns(pl.col(col).cast(currentDf.schema[col]))
            except pl.exceptions.ComputeError:
                newDf = newDf.with_columns(pl.col(col).cast(pl.Utf8))
                currentDf = currentDf.with_columns(pl.col(col).cast(pl.Utf8))
    # 컬럼 순서 맞추기
    newDf = newDf.select(currentDf.columns)
    merged = pl.concat([currentDf, newDf], how="vertical")
    merged.write_parquet(path)
    emit("edgar:incremental_done", ticker=stockCode.upper(), newRows=len(rows))


__all__ = [
    "EDGAR_DOCS_FRESHNESS_TTL_HOURS",
    "ensureEdgarDocs",
    "getLatestRegularEdgarFiling",
    "getLocalEdgarDocsState",
    "incrementalUpdateEdgarDocs",
    "isEdgarDocsCheckExpired",
    "isEdgarDocsFresh",
    "rebuildEdgarDocs",
]


# 옛 이름 (private prefix) 호환 — 외부에서 직접 부르면 안 되지만 dataLoader
# 가 기존 lazy import 로 가지고 있을 수 있어 일정 기간 alias 노출.
_ensureEdgarDocs = ensureEdgarDocs


# ── LoaderProvider 구현 + register (정공법 B — DIP) ─────────────


class EdgarDocsLoader:
    """edgarDocs 카테고리의 LoaderProvider 구현.

    core/dataLoader.py 가 직접 ensureEdgarDocs 호출 대신 registry dispatch.
    module load 시점에 _registerEdgarDocsLoader() 가 등록.
    """

    category = "edgarDocs"

    def ensure(self, stockCode, path, *, sinceYear=None, asOf=None, refresh="auto"):
        """edgarDocs 보장 — ``ensureEdgarDocs`` 위임.

        Args:
            stockCode: 종목 ticker.
            path: 저장 경로.
            sinceYear: 시작 연도 (None 이면 2009).
            asOf: 신선도 기준 시점.
            refresh: ``auto``/``force_check``/``force_rebuild``/``local_only``.

        Raises:
            ValueError: 미지원 refresh 정책.
            FileNotFoundError: ``local_only`` + 로컬 부재.

        Example:
            >>> EdgarDocsLoader().ensure("AAPL", Path("..."), sinceYear=2024)
        """
        ensureEdgarDocs(
            stockCode,
            path,
            sinceYear=sinceYear or 2009,
            asOf=asOf,
            refresh=refresh,
        )


def _registerEdgarDocsLoader() -> None:
    """import 시점 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.loaders import registerLoader

    registerLoader(EdgarDocsLoader())


_registerEdgarDocsLoader()
