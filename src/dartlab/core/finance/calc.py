"""재무 계산 공통 유틸리티 — 단일 정의.

dartlab 전체에서 중복 정의되던 수학 함수를 한 곳으로 통합.
모든 호출자는 여기서 import한다.

규칙:
- division-by-zero → None (0 반환 금지)
- None 인자 → None 반환
- 퍼센트는 *100 후 round(2)
"""

from __future__ import annotations


def safeDiv(a: float | None, b: float | None) -> float | None:
    """안전한 나눗셈. None이나 0 분모 → None."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def safePct(part: float | None, total: float | None) -> float | None:
    """안전한 퍼센트 계산. part/total * 100, round(2)."""
    r = safeDiv(part, total)
    if r is None:
        return None
    return round(r * 100, 2)


def safePctPositive(part: float | None, total: float | None) -> float | None:
    """분모가 양수일 때만 퍼센트. 적자(음수) 분모 → None."""
    if total is not None and total < 0:
        return None
    return safePct(part, total)


def cagr(start: float, end: float, years: int) -> float | None:
    """CAGR (%) 계산. start/end가 음수거나 years ≤ 0이면 None."""
    if start is None or end is None or years is None:
        return None
    if start <= 0 or end <= 0 or years <= 0:
        return None
    try:
        result = ((end / start) ** (1 / years) - 1) * 100
        if isinstance(result, complex):
            return None
        return round(result, 1)
    except (ZeroDivisionError, ValueError, OverflowError, TypeError):
        return None
