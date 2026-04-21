"""숫자 포맷 SSoT.

기존 4 곳 중복 (`display/richFrame._formatValue`, `core/select._fmtVal`,
`cli/services/output._format_number`, `credit/narrative._fmt` / `_fmtTril`) →
본 모듈로 통합.

3 가지 스타일 함수를 공개:
- :func:`formatComma` — 천단위 쉼표 (일반 숫자 표시).
- :func:`formatKr`    — 한국어 단위 (조/억/만, 선택적으로 "원" 접미사).
- :func:`formatDecimal` — 고정 소수 자릿수 + suffix (비율 %, 배수 × 등).

None / NaN 은 ``nullStr`` 로 통일. 비-숫자는 ``str(val)`` 로 pass-through.
"""

from __future__ import annotations

import math
from typing import Any


def _isNull(val: Any) -> bool:
    """None 또는 NaN 이면 True."""
    return val is None or (isinstance(val, float) and math.isnan(val))


def formatComma(val: Any, *, decimals: int = 2, nullStr: str = "-") -> str:
    """천단위 쉼표 포맷.

    Args:
        val: 숫자, None, NaN, 또는 기타 (기타는 ``str(val)``).
        decimals: float 의 소수 자릿수. ``decimals=0`` 이면 정수 반올림.
            정수-값 float 은 자동으로 정수 표기 (예: ``3.0`` → ``"3"``).
        nullStr: None / NaN 대응 문자열.

    Examples:
        >>> formatComma(1234567)
        '1,234,567'
        >>> formatComma(3.14)
        '3.14'
        >>> formatComma(3.0)
        '3'
        >>> formatComma(None)
        '-'
    """
    if _isNull(val):
        return nullStr
    if not isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, float):
        if val == int(val) and abs(val) < 1e15:
            return f"{int(val):,}"
        return f"{val:,.{decimals}f}"
    return f"{val:,}"


def formatKr(val: Any, *, withWon: bool = False, nullStr: str = "-") -> str:
    """한국어 단위 포맷 (조/억/만).

    Args:
        val: 숫자, None, NaN, 또는 기타.
        withWon: True 면 조원/억원/원 단위 (단위에 "원" 접미). False 면 조/억/만.
        nullStr: None / NaN 대응 문자열. Rich markup 도 가능 (예: ``"[dim]-[/dim]"``).

    Examples:
        >>> formatKr(1_200_000_000_000)
        '1.2조'
        >>> formatKr(5_000_000_000, withWon=True)
        '50억원'
        >>> formatKr(None, nullStr="[dim]-[/dim]")
        '[dim]-[/dim]'
    """
    if _isNull(val):
        return nullStr
    if not isinstance(val, (int, float)):
        return str(val)
    absV = abs(val)
    sign = "-" if val < 0 else ""
    if withWon:
        if absV >= 1e12:
            return f"{sign}{absV / 1e12:,.1f}조원"
        if absV >= 1e8:
            return f"{sign}{absV / 1e8:,.0f}억원"
        return f"{sign}{absV:,.0f}원"
    if absV >= 1e12:
        return f"{sign}{absV / 1e12:,.1f}조"
    if absV >= 1e8:
        return f"{sign}{absV / 1e8:,.0f}억"
    if absV >= 1e4:
        return f"{sign}{absV / 1e4:,.0f}만"
    if isinstance(val, float):
        return f"{val:,.1f}"
    return f"{val:,}"


def formatDecimal(
    val: Any,
    *,
    decimals: int = 1,
    suffix: str = "",
    nullStr: str = "N/A",
) -> str:
    """고정 소수 포맷 + suffix.

    Args:
        val: 숫자, None, NaN, 또는 기타.
        decimals: float 의 소수 자릿수.
        suffix: 뒤에 붙일 문자열 (예: ``"%"``, ``"배"``).
        nullStr: None / NaN 대응 문자열.

    Examples:
        >>> formatDecimal(3.14159, decimals=1, suffix="%")
        '3.1%'
        >>> formatDecimal(None)
        'N/A'
    """
    if _isNull(val):
        return nullStr
    if isinstance(val, float):
        return f"{val:.{decimals}f}{suffix}"
    return f"{val}{suffix}"
