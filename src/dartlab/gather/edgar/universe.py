"""gather EDGAR listed universe — SEC exchange ticker Extract.

SEC ``company_tickers_exchange.json`` fetch → listed universe parquet 캐시 갱신.

수집 일원화: 이 SEC fetch 는 gather Extract 전담. core 는 캐시 parquet read 만
(``loadEdgarListedUniverse``/``loadEdgarTargetUniverse``). providers·core build/read 가
갱신을 트리거하려면 ``core.edgarClient.updateListedUniverse`` DIP 로 본 fetch 호출.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

import polars as pl

EDGAR_LISTED_UNIVERSE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
_SEC_HEADERS = {"User-Agent": "DartLab eddmpython@gmail.com"}
LISTED_EXCHANGES = {"Nasdaq", "NYSE", "CBOE"}


def _fetchJson(url: str) -> dict:
    """SEC JSON GET — SEC fair-use User-Agent 강행.

    Args:
        url: SEC JSON endpoint.

    Returns:
        파싱된 dict payload.

    Raises:
        urllib.error.URLError: 네트워크 실패.

    Example:
        >>> _fetchJson(EDGAR_LISTED_UNIVERSE_URL)  # doctest: +SKIP
    """
    from dartlab.core.dataLoader import _socketTimeout

    with _socketTimeout():
        request = Request(url, headers=_SEC_HEADERS)
        with urlopen(request) as resp:
            return json.loads(resp.read())


def updateListedUniverse(*, force: bool = False) -> Path:
    """SEC exchange ticker 원본으로 listed universe 캐시를 갱신한다.

    캐시(``data/edgar/listedUniverse.parquet``)가 신선하면 fetch 없이 경로만 반환.
    만료/``force`` 시 SEC ``company_tickers_exchange.json`` 을 받아 cik·ticker·title·
    exchange·상장여부 컬럼으로 정규화해 parquet 저장.

    Args:
        force: 캐시 무시하고 강제 갱신.

    Returns:
        listed universe parquet ``Path``.

    Raises:
        urllib.error.URLError: 네트워크 실패.

    Example:
        >>> updateListedUniverse(force=True)  # doctest: +SKIP
    """
    from dartlab.core.dataLoader import (
        _EDGAR_UNIVERSE_TTL_HOURS,
        _getDataRoot,
        _isLocalCacheExpired,
    )
    from dartlab.core.messaging import emit

    dataRoot = _getDataRoot()
    ttlHours = _EDGAR_UNIVERSE_TTL_HOURS
    path = dataRoot / "edgar" / "listedUniverse.parquet"
    if not force and path.exists() and not _isLocalCacheExpired(path, ttlHours):
        return path

    emit("edgar:universe_update")
    data = _fetchJson(EDGAR_LISTED_UNIVERSE_URL)

    records = []
    for row in data.get("data", []):
        if len(row) < 4:
            continue
        cik, name, ticker, exchange = row[:4]
        tickerStr = str(ticker or "").upper().strip()
        exchangeStr = str(exchange or "").strip()
        if not tickerStr:
            continue
        records.append(
            {
                "cik": str(cik).zfill(10),
                "ticker": tickerStr,
                "title": str(name or "").strip(),
                "exchange": exchangeStr,
                "is_exchange_listed": exchangeStr in LISTED_EXCHANGES,
                "is_otc": exchangeStr == "OTC",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(records).write_parquet(path)
    emit("edgar:universe_save", path=str(path))
    return path


__all__ = ["EDGAR_LISTED_UNIVERSE_URL", "updateListedUniverse"]
