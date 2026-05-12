"""KRX data.krx.co.kr 상장법인 목록 — JSON API + 24h TTL 캐시.

KIND 목록 (registry.py) 보다 상세 컬럼 (full_code 12자리 ISIN, marketName 시장구분) 제공.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import httpx
import polars as pl

from dartlab.gather.infra.ttl import TTL_LISTING as CACHE_TTL

log = logging.getLogger(__name__)

_KRX_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
_KRX_DATA = {
    "locale": "ko_KR",
    "mktsel": "ALL",
    "typeNo": "0",
    "searchText": "",
    "bld": "dbms/comm/finder/finder_stkisu",
}
_KRX_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
}

_krxMemory: pl.DataFrame | None = None
_krxMemoryTs: float = 0.0
_krxMemoryLock = threading.Lock()


def _krxCacheFile() -> Path:
    """KRX 상장법인 캐시 파일 경로 반환.

    Returns
    -------
    Path
        ``{dataRoot}/krxList/corpList.parquet`` 경로.
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "krxList" / "corpList.parquet"


def _fetchKrx() -> pl.DataFrame:
    """KRX data.krx.co.kr JSON API에서 상장법인 목록 수집.

    네트워크 실패·HTTP 오류·JSON 파싱 실패 시 빈 DataFrame 반환.

    Returns
    -------
    pl.DataFrame
        full_code : str — ISIN 전체 코드 (12자리)
        short_code : str — 단축 종목코드 (6자리)
        codeName : str — 종목명
        marketName : str — 시장구분 (KOSPI/KOSDAQ/KONEX)
    """
    schema = {
        "full_code": pl.Utf8,
        "short_code": pl.Utf8,
        "codeName": pl.Utf8,
        "marketName": pl.Utf8,
    }
    try:
        r = httpx.post(
            _KRX_URL,
            data=_KRX_DATA,
            headers=_KRX_HEADERS,
            timeout=30,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        log.warning("KRX 상장법인 목록 수집 실패: %s", exc)
        return pl.DataFrame(schema=schema)

    if r.status_code != 200:
        log.warning("KRX 상장법인 목록 HTTP %d", r.status_code)
        return pl.DataFrame(schema=schema)

    try:
        jo = json.loads(r.text)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("KRX 응답 JSON 파싱 실패: %s", exc)
        return pl.DataFrame(schema=schema)

    block = jo.get("block1", [])
    if not block:
        log.warning("KRX 응답에 block1 데이터 없음")
        return pl.DataFrame(schema=schema)

    df = pl.DataFrame(block)
    return df


def _loadKrxCache() -> pl.DataFrame | None:
    """KRX 파일 캐시 로드. TTL(24h) 초과면 None.

    Returns
    -------
    pl.DataFrame | None
        캐시된 KRX 상장법인 DataFrame. 없거나 만료 시 None.
    """
    path = _krxCacheFile()
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        return None
    return pl.read_parquet(str(path))


def _saveKrxCache(df: pl.DataFrame) -> None:
    """KRX 상장법인 DataFrame을 Parquet 파일로 캐시 저장.

    Parameters
    ----------
    df : pl.DataFrame
        저장할 KRX 상장법인 DataFrame.
    """
    path = _krxCacheFile()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(path))


def getKrxList(*, forceRefresh: bool = False) -> pl.DataFrame:
    """KRX data.krx.co.kr 상장법인 전체 목록.

    Capabilities: ISIN full_code + short_code + marketName (KOSPI/KOSDAQ/KONEX) 제공.
    AIContext: KIND 보다 상세한 시장구분 + ISIN — quant/scan universe 빌더 진입.
    Guide: forceRefresh=True 시 KRX HTTP 강제 재요청. JSON API 무인증.
    When: KIND 와 별개 KRX ISIN/시장구분 매핑 필요 시.
    How: 메모리 → 파일 → KRX data API JSON 호출 → DataFrame.

    캐시 우선순위: 메모리 -> 파일(24h TTL) -> KRX API.
    KIND 목록보다 상세 컬럼(full_code, short_code, marketName 등) 제공.

    Parameters
    ----------
    forceRefresh : bool
        True면 캐시 무시하고 KRX API 재요청. 기본 False.

    Returns
    -------
    pl.DataFrame
        full_code : str — ISIN 전체 코드 (12자리)
        short_code : str — 단축 종목코드 (6자리)
        codeName : str — 종목명
        marketName : str — 시장구분 (KOSPI/KOSDAQ/KONEX)

    Raises
    ------
    없음
        KRX API 실패 시 빈 DataFrame 반환 (예외 흡수).

    Example
    -------
    >>> df = getKrxList()
    """
    global _krxMemory, _krxMemoryTs

    if not forceRefresh and _krxMemory is not None:
        if (time.time() - _krxMemoryTs) < CACHE_TTL:
            return _krxMemory

    with _krxMemoryLock:
        if not forceRefresh and _krxMemory is not None:
            if (time.time() - _krxMemoryTs) < CACHE_TTL:
                return _krxMemory

        if not forceRefresh:
            cached = _loadKrxCache()
            if cached is not None:
                _krxMemory = cached
                _krxMemoryTs = time.time()
                return cached

        from dartlab.core.messaging import emit

        emit("listing:krx:download")
        df = _fetchKrx()
        if df.height > 0:
            _saveKrxCache(df)
        _krxMemory = df
        _krxMemoryTs = time.time()
        emit("listing:krx:done", count=df.height)
        return df
