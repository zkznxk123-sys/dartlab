"""Gather 도메인 fallback 체인 + loader — __init__ thin 룰을 위한 분리.

`__init__.py` 의 thin facade 룰 (룰 4) 을 위해 함수/상수 정의 분리.
호출자는 `from dartlab.gather.domains import X` 그대로 사용 (re-export).
"""

from __future__ import annotations

from ..marketConfig import getMarketConfig

# 데이터 유형별 fallback 순서 (KR 기본값 — 하위호환)
PRICE_FALLBACK = ["naver", "naverGlobal"]
CONSENSUS_FALLBACK = ["naver"]
FLOW_FALLBACK = ["naver"]
DIVIDENDS_FALLBACK = ["fmp"]
HISTORY_FALLBACK = ["fdr", "yahooChart", "naverGlobal", "fmp"]


def getPriceFallback(market: str = "KR") -> list[str]:
    """시장별 주가 fallback 체인.

    Capabilities: marketConfig 에 등록된 시장별 fallback 도메인 list.
    AIContext: sources/price.fetch 의 chain 순서 SSOT.
    Guide: list 순서 = 우선순위 (첫 항목 = primary).
    When: gather.price 진입 시 chain 구성 단계.
    How: getMarketConfig(market) → config.fallback_chain → list.

    Parameters
    ----------
    market : str
        시장 코드 (``"KR"`` | ``"US"`` 등). 기본값 ``"KR"``.

    Returns
    -------
    list[str]
        도메인 이름 목록 (우선순위 순).
        예: ``["naver", "naverGlobal"]`` (KR), ``["fmp"]`` (US).

    Raises
    ------
    KeyError
        marketConfig 에 등록되지 않은 market 코드일 때.

    Example
    -------
    >>> getPriceFallback("KR")
    ['naver', 'naverGlobal']
    """
    config = getMarketConfig(market)
    return list(config.fallback_chain)


# marketConfig.fallback_chain 의 source 표시 이름 (사용자 visible) → 모듈 이름 (camelCase) alias.
# fallback_chain 의 snake 표기는 PriceSnapshot.source 등 사용자 노출에 그대로 사용.
_DOMAIN_ALIASES: dict[str, str] = {
    "naver_global": "naverGlobal",
    "yahoo_chart": "yahooChart",
}


def loadDomain(name: str):
    """도메인 모듈 lazy import.

    Capabilities: 도메인 이름 → Python 모듈 lazy import (snake/camel alias).
    AIContext: fallback chain 의 dispatch — source 이름 → fetch* 함수 모음 매핑.
    Guide: snake_case (naver_global) 와 camelCase (naverGlobal) 모두 동일 모듈.
    When: sources/{price,flow,history}.fetch 의 chain iterate 시.
    How: _DOMAIN_ALIASES 정규화 → if/elif 분기 → 모듈 import.

    Parameters
    ----------
    name : str
        도메인 식별자. ``"naver"`` | ``"fmp"`` | ``"krx"`` | ``"fdr"``
        | ``"naverGlobal"`` | ``"yahooChart"``. snake_case alias 도 허용
        (``"naver_global"``, ``"yahoo_chart"``) — fallback_chain 의 source 표시 이름.

    Returns
    -------
    module
        해당 도메인의 Python 모듈 객체. ``fetchPrice`` 등 함수를 포함.

    Raises
    ------
    ValueError
        등록되지 않은 도메인 이름일 때.

    Example
    -------
    >>> mod = loadDomain("naver")
    """
    canonical = _DOMAIN_ALIASES.get(name, name)
    if canonical == "naver":
        from . import naver

        return naver

    if canonical == "fmp":
        from . import fmp

        return fmp
    if canonical == "krx":
        from . import krx

        return krx
    if canonical == "fdr":
        from . import fdr

        return fdr
    if canonical == "naverGlobal":
        from . import naverGlobal

        return naverGlobal
    if canonical == "yahooChart":
        from . import yahooChart

        return yahooChart
    raise ValueError(f"알 수 없는 도메인: {name}")
