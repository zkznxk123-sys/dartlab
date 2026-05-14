"""시장 자동 감지 — 종목코드/티커/회사명으로 KR/US 판별.

모든 엔진이 이 모듈을 SSOT로 사용한다.
market 파라미터 기본값이 "KR"인 곳에서 resolveMarket을 호출하면
알파벳 종목코드는 자동으로 US로 분기된다.

Usage::

    from dartlab.core.market import detectMarket, resolveMarket

    detectMarket("005930")   # "KR"
    detectMarket("INTC")     # "US"
    detectMarket("삼성전자")  # "KR"

    resolveMarket("INTC", "KR")    # "US" (알파벳 → 자동 감지)
    resolveMarket("005930", "KR")  # "KR" (6자리 숫자 → 그대로)
    resolveMarket("INTC", "US")    # "US" (명시 → 그대로)
"""

from __future__ import annotations

import re

_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")


def detectMarket(code: str) -> str:
    """종목코드/티커/회사명 → "KR" | "US" 자동 감지.

    Capabilities:
        6자리 숫자, 한글 회사명, 영문 티커를 구분해 KR/US 시장 코드를 반환한다.
    AIContext:
        Company, gather, scan 진입점이 사용자의 코드 문자열만 보고 provider를 고를 때
        참조하는 L0 시장 판별 함수다.
    Guide:
        명시 market 값이 있는 경우에는 resolveMarket을 쓰고, 순수 문자열 판별만 필요할
        때 이 함수를 직접 쓴다.
    When:
        public API가 "005930", "INTC", "삼성전자" 같은 입력을 받았을 때.
    How:
        공백 제거 후 6자리 숫자와 한글을 KR로, 알파벳 포함 문자열을 US로 분류한다.

    Parameters
    ----------
    code : str
        종목코드 ("005930"), 티커 ("INTC"), 또는 회사명 ("삼성전자").

    Returns
    -------
    str
        "KR" — 6자리 숫자 또는 한글 포함.
        "US" — 알파벳 포함 (영문 티커).
    Requires:
        code는 문자열이어야 한다. 빈 문자열은 KR fallback으로 처리한다.
    Raises:
        AttributeError: code가 strip 메서드를 제공하지 않는 비문자 객체일 때.
    Example:
        >>> detectMarket("005930")
        'KR'
        >>> detectMarket("INTC")
        'US'
    SeeAlso:
        resolveMarket: 명시 market 파라미터와 자동 감지를 함께 처리한다.
    """
    if not code:
        return "KR"
    stripped = code.strip()
    # 6자리 숫자 → KR
    if stripped.isdigit() and len(stripped) == 6:
        return "KR"
    # 한글 포함 → KR (회사명)
    if _HANGUL_RE.search(stripped):
        return "KR"
    # 알파벳 포함 → US
    if any(c.isalpha() for c in stripped):
        return "US"
    # 숫자만 (6자리 아닌) → KR fallback
    return "KR"


def resolveMarket(code: str, market: str = "auto") -> str:
    """market 파라미터 해석 — 명시 값 우선, 아니면 자동 감지.

    Capabilities:
        사용자 market 인자와 code 기반 자동 감지를 합쳐 최종 KR/US 시장 코드를 정한다.
    AIContext:
        public surface가 기본 market을 KR처럼 보존하면서도 영문 티커를 US provider로
        보내기 위한 L0 routing guard다.
    Guide:
        provider 선택 직전에 호출한다. market="US"는 강제값이고, "auto" 또는 "KR"은
        code 형태를 다시 본다.
    When:
        Company, gather, scan, quant 계열 진입점에서 market 기본값을 해석할 때.
    How:
        market을 대문자로 정규화하고, US는 그대로 반환하며 AUTO/KR은 detectMarket으로
        위임한다.

    market="KR"(기본값)이어도 code가 알파벳이면 US로 자동 변경.
    market을 "US"로 명시했으면 그대로 유지.

    Parameters
    ----------
    code : str
        종목코드/티커/회사명.
    market : str
        "KR" | "US" | "auto". 기본 "auto".

    Returns
    -------
    str
        "KR" 또는 "US".
    Requires:
        code와 market은 문자열 또는 None 호환 값이어야 한다.
    Raises:
        AttributeError: code가 비어 있지 않지만 strip 메서드가 없는 객체일 때.
    Example:
        >>> resolveMarket("INTC", "KR")
        'US'
        >>> resolveMarket("005930", "KR")
        'KR'
    SeeAlso:
        detectMarket: code 단독 자동 감지.
    """
    if not code:
        return market.upper() if market and market.lower() != "auto" else "KR"

    upper = market.upper() if market else "KR"

    # 명시적으로 US를 지정했으면 그대로
    if upper == "US":
        return "US"

    # "auto" 또는 "KR"(기본값)인데 코드가 알파벳이면 자동 감지
    if upper in ("AUTO", "KR"):
        return detectMarket(code)

    return upper
