"""내부자 거래 facade -- KR(DART)."""

from __future__ import annotations

import logging

from .types import InsiderTrade, MajorHolder

log = logging.getLogger(__name__)


async def fetchInsiderTrading(
    stockCode: str,
    *,
    market: str = "KR",
    **_kwargs,
) -> list[InsiderTrade]:
    """내부자(임원/주요주주) 거래 내역 -- KR만 지원.

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 빈 리스트 반환.

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
    """
    if market != "KR":
        return []
    try:
        from .domains.dartApi import fetchInsiderTrading as _dartInsider

        return await _dartInsider(stockCode)
    except (ImportError, OSError) as exc:
        log.warning("insider KR 실패 (%s): %s", stockCode, exc)
        return []


async def fetchMajorShareholders(
    stockCode: str,
    *,
    market: str = "KR",
    **_kwargs,
) -> list[MajorHolder]:
    """5% 이상 대량보유 변동 -- KR(DART).

    Parameters
    ----------
    stockCode : str
        종목코드 (예: "005930").
    market : str
        시장 코드. "KR"만 지원, 그 외 빈 리스트 반환.

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
    """
    if market != "KR":
        return []
    try:
        from .domains.dartApi import fetchMajorShareholders as _dartMajor

        return await _dartMajor(stockCode)
    except (ImportError, OSError) as exc:
        log.warning("majorShareholders 실패 (%s): %s", stockCode, exc)
        return []
