"""내부자 거래 facade -- KR(DART)."""

from __future__ import annotations

import logging

from ..types import InsiderTrade, MajorHolder

log = logging.getLogger(__name__)


async def fetchInsiderTrading(
    stockCode: str,
    *,
    market: str = "KR",
    limit: int | None = None,
    **_kwargs,
) -> list[InsiderTrade]:
    """내부자(임원/주요주주) 거래 내역 -- KR만 지원.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 빈 리스트 반환.
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns
    -------
    list[InsiderTrade]
        내부자 거래 리스트. 각 InsiderTrade 필드:

        - date : str — 거래일 (YYYY-MM-DD)
        - name : str — 거래자 이름
        - position : str — 직위/관계
        - tradeType : str — 거래 유형 (취득/처분/장내매수/장내매도)
        - changeShares : int — 변동 주식수 (주)
        - afterShares : int — 변동 후 보유 주식수 (주)
        - reason : str — 변동 사유

        KR 외 시장이거나 조회 실패 시 빈 리스트 [].

    Requires:
        KR: DART_API_KEY env (providers/dart/ops/insiderTrades).

    Raises
    ------
    없음
        provider 내부 예외 (ImportError/OSError/TypeError) 는 흡수.

    Example
    -------
    >>> trades = await fetchInsiderTrading("005930", market="KR", limit=10)
    """
    if market != "KR":
        return []
    try:
        from dartlab.providers.dart.ops.insiderTrades import fetchInsiderTradingRaw

        rawRows = await fetchInsiderTradingRaw(stockCode)
        rows = [InsiderTrade(**row) for row in rawRows]
        if limit is not None and limit > 0:
            return rows[:limit]
        return rows
    except (ImportError, OSError, TypeError) as exc:
        log.warning("insider KR 실패 (%s): %s", stockCode, exc)
        return []


async def fetchMajorShareholders(
    stockCode: str,
    *,
    market: str = "KR",
    limit: int | None = None,
    **_kwargs,
) -> list[MajorHolder]:
    """5% 이상 대량보유 변동 -- KR(DART).

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 빈 리스트 반환.
    limit : int | None
        반환 행수 상한 (가장 최근 N건). None이면 전체.

    Returns
    -------
    list[MajorHolder]
        대량보유 주주 리스트. 각 MajorHolder 필드:

        - holderName : str — 보유자 이름
        - shares : int — 보유 주식수 (주)
        - ratio : float — 보유비율 (%)
        - changeDate : str — 변동일 (YYYY-MM-DD)
        - changeType : str — 변동 유형 (취득/처분/변동)

        KR 외 시장이거나 조회 실패 시 빈 리스트 [].

    Requires:
        KR: DART_API_KEY env (providers/dart/ops/insiderTrades).

    Raises
    ------
    없음
        provider 내부 예외 (ImportError/OSError/TypeError) 는 흡수.

    Example
    -------
    >>> holders = await fetchMajorShareholders("005930", market="KR", limit=10)
    """
    if market != "KR":
        return []
    try:
        from dartlab.providers.dart.ops.insiderTrades import fetchMajorShareholdersRaw

        rawRows = await fetchMajorShareholdersRaw(stockCode)
        rows = [MajorHolder(**row) for row in rawRows]
        if limit is not None and limit > 0:
            return rows[:limit]
        return rows
    except (ImportError, OSError, TypeError) as exc:
        log.warning("majorShareholders 실패 (%s): %s", stockCode, exc)
        return []


def iterFetchInsiderTrading(
    stockCode: str,
    *,
    market: str = "KR",
    batchSize: int = 100,
):
    """fetchInsiderTrading 의 streaming pair — list 를 batchSize 단위 yield (A 트랙 I2).

    Capabilities: list[InsiderTrade] 를 batchSize slice yield.
    AIContext: informed trading 흐름의 chunk 처리.
    Guide: fetch 가 빈 list 면 yield 없음.
    When: 내부자 거래가 많은 회사의 chunk 처리 시.
    How: runAsync(fetchInsiderTrading) → list slice iterate.

    Args:
        stockCode: 종목코드.
        market: 시장. "KR"만 지원.
        batchSize: batch 크기.

    Yields:
        list[InsiderTrade] — 각 batch.

    Raises:
        없음.

    Example::

        for batch in iterFetchInsiderTrading("005930", batchSize=50): process(batch)

    Requires: KR DART_API_KEY env.
    See Also: ``fetchInsiderTrading``.
    """
    from ..infra.http import runAsync

    trades = runAsync(fetchInsiderTrading(stockCode, market=market))
    if not trades:
        return
    for i in range(0, len(trades), batchSize):
        yield trades[i : i + batchSize]


def iterFetchMajorShareholders(
    stockCode: str,
    *,
    market: str = "KR",
    batchSize: int = 100,
):
    """fetchMajorShareholders 의 streaming pair — list 를 batchSize 단위 yield (A 트랙 I2).

    Capabilities: list[MajorHolder] 를 batchSize slice yield.
    AIContext: 5% 보유 변동의 chunk 처리 — 시계열 활동 timeline.
    Guide: fetch 가 빈 list 면 yield 없음.
    When: 대량보유 변동이 많은 회사의 chunk 처리 시.
    How: runAsync(fetchMajorShareholders) → list slice iterate.

    Args:
        stockCode: 종목코드.
        market: 시장. "KR"만 지원.
        batchSize: batch 크기.

    Yields:
        list[MajorHolder] — 각 batch.

    Raises:
        없음.

    Example::

        for batch in iterFetchMajorShareholders("005930"): process(batch)

    Requires: KR DART_API_KEY env.
    See Also: ``fetchMajorShareholders``.
    """
    from ..infra.http import runAsync

    holders = runAsync(fetchMajorShareholders(stockCode, market=market))
    if not holders:
        return
    for i in range(0, len(holders), batchSize):
        yield holders[i : i + batchSize]
