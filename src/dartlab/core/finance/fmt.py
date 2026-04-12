"""통화별 포맷팅 헬퍼 — 재무 금액/가격/단위 SSOT."""

from __future__ import annotations


def fmtBig(value: float | None, currency: str = "KRW") -> str:
    """대규모 금액 포맷.

    KRW: 조/억/만/기본 자동 전환 (>=1e12 조, >=1e8 억, >=1e4 만, 그 외 원)
    USD: M 단위
    None → "-"
    """
    if value is None:
        return "-"
    if currency == "USD":
        return f"${value / 1e6:,.0f}M"
    av = abs(value)
    if av >= 1e12:
        return f"{value / 1e12:,.1f}조"
    if av >= 1e8:
        return f"{value / 1e8:,.0f}억"
    if av >= 1e4:
        return f"{value / 1e4:,.0f}만"
    return f"{value:,.0f}"


def fmtPrice(value: float | None, currency: str = "KRW") -> str:
    """주당 가격 포맷 (원/$). None → "-"."""
    if value is None:
        return "-"
    if currency == "USD":
        return f"${value:,.2f}"
    return f"{value:,.0f}원"


def fmtNum(value: float | None, suffix: str = "", precision: int = 1) -> str:
    """일반 숫자 포맷 + suffix. None → "-"."""
    if value is None:
        return "-"
    return f"{value:,.{precision}f}{suffix}"


def fmtUnit(currency: str = "KRW") -> str:
    """통화 단위 레이블."""
    if currency == "USD":
        return "$"
    return "원"
