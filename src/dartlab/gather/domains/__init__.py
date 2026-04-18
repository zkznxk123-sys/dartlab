"""Gather 도메인 레지스트리 — fallback 순서 정의."""

from __future__ import annotations

from ..market_config import get_market_config

# 데이터 유형별 fallback 순서 (KR 기본값 — 하위호환)
PRICE_FALLBACK = ["naver", "naver_global"]
CONSENSUS_FALLBACK = ["naver"]
FLOW_FALLBACK = ["naver"]
DIVIDENDS_FALLBACK = ["fmp"]
HISTORY_FALLBACK = ["fdr", "yahoo_chart", "naver_global", "fmp"]


def get_price_fallback(market: str = "KR") -> list[str]:
    """시장별 주가 fallback 체인.

    Parameters
    ----------
    market : str
        시장 코드 (``"KR"`` | ``"US"`` 등). 기본값 ``"KR"``.

    Returns
    -------
    list[str]
        도메인 이름 목록 (우선순위 순).
        예: ``["naver", "naver_global"]`` (KR), ``["fmp"]`` (US).
    """
    config = get_market_config(market)
    return list(config.fallback_chain)


def load_domain(name: str):
    """도메인 모듈 lazy import.

    Parameters
    ----------
    name : str
        도메인 식별자. ``"naver"`` | ``"fmp"`` | ``"krx"`` | ``"fdr"``
        | ``"naver_global"`` | ``"yahoo_chart"``.

    Returns
    -------
    module
        해당 도메인의 Python 모듈 객체. ``fetch_price`` 등 함수를 포함.

    Raises
    ------
    ValueError
        등록되지 않은 도메인 이름일 때.
    """
    if name == "naver":
        from . import naver

        return naver

    if name == "fmp":
        from . import fmp

        return fmp
    if name == "krx":
        from . import krx

        return krx
    if name == "fdr":
        from . import fdr

        return fdr
    if name == "naver_global":
        from . import naver_global

        return naver_global
    if name == "yahoo_chart":
        from . import yahoo_chart

        return yahoo_chart
    raise ValueError(f"알 수 없는 도메인: {name}")
