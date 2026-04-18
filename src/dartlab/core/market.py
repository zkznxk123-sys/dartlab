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

    Parameters
    ----------
    code : str
        종목코드 ("005930"), 티커 ("INTC"), 또는 회사명 ("삼성전자").

    Returns
    -------
    str
        "KR" — 6자리 숫자 또는 한글 포함.
        "US" — 알파벳 포함 (영문 티커).
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
