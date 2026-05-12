"""Financial Modeling Prep — API 키 기반 보조 소스.

무료 플랜: 250 req/day. API 키 없으면 자동 skip (다음 fallback으로).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from ..marketConfig import resolveTicker
from ..types import GatherError, PriceSnapshot

log = logging.getLogger(__name__)

_BASE = "https://financialmodelingprep.com/api/v3"


def _getApiKey() -> str | None:
    """환경변수에서 FMP API 키를 조회.

    Returns
    -------
    str | None
        ``FMP_API_KEY`` 환경변수 값. 미설정 시 None.
    """
    return os.environ.get("FMP_API_KEY")


async def fetchPrice(
    stockCode: str,
    client,
    *,
    market: str = "US",
    limit: int | None = None,
) -> PriceSnapshot | None:
    """현재가 — FMP /quote/{ticker}.

    Capabilities: US FMP /quote/{ticker} fetch + PriceSnapshot 변환.
    AIContext: US gather.price fallback chain — Yahoo 다음 single-shot.
    Guide: FMP_API_KEY env 필요. 미설정 시 None.
    When: Yahoo 실패 후 fallback / US 가격 보조 source.
    How: financialmodelingprep.com /quote JSON → PriceSnapshot.

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"AAPL"``, ``"005930"``).
    client
        비동기 HTTP 클라이언트.
    market : str
        시장 코드 (기본값 ``"US"``).
    limit : int | None
        단건 PriceSnapshot 반환 함수라 무시된다. 인터페이스 호환 목적.

    Returns
    -------
    PriceSnapshot | None
        현재가 스냅샷. 주요 필드:

        - current : float — 현재가 (해당 통화 단위)
        - change : float — 전일 대비 변동액
        - change_pct : float — 전일 대비 변동률 (%)
        - high_52w : float — 52주 최고가
        - low_52w : float — 52주 최저가
        - volume : int — 거래량 (주)
        - market_cap : float — 시가총액
        - per : float | None — PER (배)
        - source : str — ``"fmp"``

        API 키 미설정이거나 조회 실패 시 None.

    Raises
    ------
    없음
        GatherError/ValueError 등 내부 예외는 None 반환으로 흡수.

    Example
    -------
    >>> snap = await fetchPrice("AAPL", client, market="US")
    """
    del limit
    key = _getApiKey()
    if not key:
        return None  # 키 없으면 skip

    ticker = resolveTicker(stockCode, market, "fmp")

    try:
        resp = await client.get(
            f"{_BASE}/quote/{ticker}",
            params={"apikey": key},
        )
    except GatherError:
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    if not data or not isinstance(data, list) or len(data) == 0:
        return None

    q = data[0]
    current = q.get("price", 0.0)
    if not current:
        return None

    return PriceSnapshot(
        current=current,
        change=q.get("change", 0.0),
        change_pct=q.get("changesPercentage", 0.0),
        high_52w=q.get("yearHigh", 0.0),
        low_52w=q.get("yearLow", 0.0),
        volume=q.get("volume", 0),
        marketCap=q.get("marketCap", 0.0),
        per=q.get("pe") if q.get("pe") else None,
        pbr=None,
        dividend_yield=None,
        source="fmp",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        currency=q.get("currency", "USD"),
        exchange=q.get("exchange", ""),
        market=market,
    )


async def fetchHistory(
    stockCode: str,
    client,
    *,
    start: str,
    end: str,
    market: str = "US",
    limit: int | None = None,
) -> list[dict]:
    """히스토리 OHLCV — FMP /historical-price-full/{ticker}.

    Capabilities: US FMP 일별 OHLCV history list[dict].
    AIContext: US history fallback chain — Yahoo 실패 시 backup.
    Guide: FMP_API_KEY env 필요. start/end YYYY-MM-DD.
    When: Yahoo 실패 + US 일별 OHLCV 필요 시.
    How: financialmodelingprep.com /historical-price-full → list[dict].

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"AAPL"``).
    client
        비동기 HTTP 클라이언트.
    start : str
        시작일 (YYYY-MM-DD).
    end : str
        종료일 (YYYY-MM-DD).
    market : str
        시장 코드 (기본값 ``"US"``).
    limit : int | None
        반환 행수 상한 (가장 최근 N일). None이면 [start, end] 전체.

    Returns
    -------
    list[dict]
        OHLCV 행 목록 (날짜 오름차순). 각 dict 키:

        - date : str — 거래일 (YYYY-MM-DD)
        - open : float — 시가
        - high : float — 고가
        - low : float — 저가
        - close : float — 종가
        - volume : int — 거래량 (주)

        API 키 미설정이거나 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        GatherError 등 내부 예외는 빈 리스트로 흡수.

    Example
    -------
    >>> rows = await fetchHistory("AAPL", client, start="2024-01-01", end="2024-12-31")
    """
    key = _getApiKey()
    if not key:
        return []

    ticker = resolveTicker(stockCode, market, "fmp")

    try:
        resp = await client.get(
            f"{_BASE}/historical-price-full/{ticker}",
            params={"apikey": key, "from": start, "to": end},
        )
    except GatherError:
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    historical = data.get("historical", [])
    if not historical:
        return []

    rows = []
    for h in reversed(historical):  # FMP는 최신→과거 순 → 역순
        rows.append(
            {
                "date": h.get("date", ""),
                "open": h.get("open", 0.0),
                "high": h.get("high", 0.0),
                "low": h.get("low", 0.0),
                "close": h.get("close", 0.0),
                "volume": h.get("volume", 0),
            }
        )

    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


async def fetchDividends(
    stockCode: str,
    client,
    *,
    market: str = "US",
    limit: int | None = None,
) -> list[dict]:
    """배당 이력 — FMP /historical-price-full/stock_dividend.

    Capabilities: US FMP 배당 이력 list[dict] (date, dividend).
    AIContext: gather.dividends US backend — naverGlobal fallback.
    Guide: FMP_API_KEY 필요. 미설정 시 빈 list.
    When: US 종목 배당 이력 분석 시.
    How: financialmodelingprep.com stock_dividend → list[dict].

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"AAPL"``).
    client
        비동기 HTTP 클라이언트.
    market : str
        시장 코드 (기본값 ``"US"``).
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns
    -------
    list[dict]
        배당 내역 (날짜 오름차순). 각 dict 키:

        - date : str — 배당 기준일 (YYYY-MM-DD)
        - amount : float — 주당 배당금 (해당 통화 단위)

        API 키 미설정이거나 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        GatherError 등 내부 예외는 빈 리스트로 흡수.

    Example
    -------
    >>> divs = await fetchDividends("AAPL", client)
    """
    key = _getApiKey()
    if not key:
        return []

    ticker = resolveTicker(stockCode, market, "fmp")
    try:
        resp = await client.get(
            f"{_BASE}/historical-price-full/stock_dividend/{ticker}",
            params={"apikey": key},
        )
    except GatherError:
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    historical = data.get("historical", [])
    rows = []
    for h in historical:
        date = h.get("date", "")
        amount = h.get("dividend", 0.0) or h.get("adjDividend", 0.0)
        if date and amount:
            rows.append({"date": date, "amount": amount})
    out = sorted(rows, key=lambda x: x["date"])
    if limit is not None and limit > 0:
        return out[-limit:]
    return out


async def fetchSplits(
    stockCode: str,
    client,
    *,
    market: str = "US",
    limit: int | None = None,
) -> list[dict]:
    """분할 이력 — FMP /historical-price-full/stock_split.

    Capabilities: US FMP 액면분할 이력 list[dict] (date, ratio).
    AIContext: gather.splits US backend — naverGlobal fallback.
    Guide: FMP_API_KEY 필요.
    When: US 종목 분할 이력 / 보정 검증 시.
    How: financialmodelingprep.com stock_split → list[dict].

    Parameters
    ----------
    stock_code : str
        종목코드 (예: ``"AAPL"``).
    client
        비동기 HTTP 클라이언트.
    market : str
        시장 코드 (기본값 ``"US"``).
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns
    -------
    list[dict]
        분할 내역 (날짜 오름차순). 각 dict 키:

        - date : str — 분할 기준일 (YYYY-MM-DD)
        - numerator : int — 분할 비율 분자
        - denominator : int — 분할 비율 분모

        API 키 미설정이거나 조회 실패 시 빈 리스트.

    Raises
    ------
    없음
        GatherError 등 내부 예외는 빈 리스트로 흡수.

    Example
    -------
    >>> splits = await fetchSplits("AAPL", client)
    """
    key = _getApiKey()
    if not key:
        return []

    ticker = resolveTicker(stockCode, market, "fmp")
    try:
        resp = await client.get(
            f"{_BASE}/historical-price-full/stock_split/{ticker}",
            params={"apikey": key},
        )
    except GatherError:
        return []

    try:
        data = resp.json()
    except ValueError:
        return []

    historical = data.get("historical", [])
    rows = []
    for h in historical:
        date = h.get("date", "")
        numerator = h.get("numerator", 1)
        denominator = h.get("denominator", 1)
        if date:
            rows.append({"date": date, "numerator": numerator, "denominator": denominator})
    out = sorted(rows, key=lambda x: x["date"])
    if limit is not None and limit > 0:
        return out[-limit:]
    return out
