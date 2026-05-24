"""회계 정합 Decimal 헬퍼 — T7-4 트랙.

float epsilon 오차가 의사결정에 영향을 주는 곳 (재무비율 비교 / Z-score zone /
신용 등급 threshold / 회계 등식) 에서 사용. Polars 수치 컬럼은 float 유지 —
본 모듈은 *경계 비교* 와 *외부 보고용 단일 값* 에 한정.

사용 위치 (T7-4 marc):
    - `analysis/ratios.py` — 동등 비교 (PBR < 1.0)
    - `analysis/cashflow.py` — 회계 등식 (자산 = 부채 + 자본 검증)
    - `credit/altman.py` — Z-score zone threshold (1.81, 2.99)
    - `story/builders.py` — 비교 동등 판정
    - `viz/display/finance/*` — 표시 직전 반올림

원칙:
    1. **DataFrame 안 numeric 컬럼은 float 유지** — Polars Decimal 지원이 아직
       제한적 + 대량 데이터 성능 부담. 본 모듈은 *경계* 만.
    2. **반올림 일관성** — `HALF_EVEN` (banker's rounding) 기본. 회계 표준 정합.
    3. **단위 명시** — `toDecimal(value, unit="krw")` 처럼 의미 단위 동행.
"""

from __future__ import annotations

import decimal as _decimal
from decimal import Decimal
from typing import Any

# 회계 표준 정밀도 — 28 자리 (Decimal default). 한국 K-IFRS 의 원 단위 + 소수 8 자리 충분.
_decimal.getcontext().prec = 28
_decimal.getcontext().rounding = _decimal.ROUND_HALF_EVEN


def toDecimal(value: Any, *, default: Decimal | None = None) -> Decimal:
    """안전 변환 — float/int/str → Decimal.

    Args:
        value: 변환 대상. None / NaN / inf 는 default 또는 ValueError.
        default: 변환 실패 시 반환할 값. None 이면 ValueError.
    Returns:
        Decimal 인스턴스.
    Example:
        >>> toDecimal("123.45")
        Decimal('123.45')
        >>> toDecimal(0.1 + 0.2, default=Decimal("0"))
        Decimal('0.30000000000000004...')  # float epsilon 보존 — 신뢰 X
    Guide:
        float → Decimal 변환은 *epsilon 보존* 이라 신뢰 X. 가능하면 str 입력.
    """
    if value is None:
        if default is not None:
            return default
        raise ValueError("toDecimal: value is None")
    try:
        # str 우회 — float epsilon 흡수.
        if isinstance(value, float):
            if value != value:  # NaN check (NaN != NaN)
                if default is not None:
                    return default
                raise ValueError("toDecimal: NaN")
            if value in (float("inf"), float("-inf")):
                if default is not None:
                    return default
                raise ValueError(f"toDecimal: infinity {value}")
            return Decimal(str(value))
        return Decimal(value)
    except (_decimal.InvalidOperation, TypeError, ValueError):
        if default is not None:
            return default
        raise


def roundDecimal(value: Decimal | float | str, *, places: int = 2) -> Decimal:
    """반올림 — banker's rounding (HALF_EVEN, 회계 표준).

    Args:
        value: 반올림 대상.
        places: 소수 자리수 (기본 2 — 통화 단위 정합).
    Returns:
        Decimal.
    Example:
        >>> roundDecimal("2.5", places=0)
        Decimal('2')
        >>> roundDecimal("3.5", places=0)
        Decimal('4')
        >>> roundDecimal(0.1 + 0.2, places=2)
        Decimal('0.30')
    """
    d = toDecimal(value)
    quant = Decimal("1") if places == 0 else Decimal("1").scaleb(-places)
    return d.quantize(quant, rounding=_decimal.ROUND_HALF_EVEN)


def isClose(a: Any, b: Any, *, absTol: str | Decimal = "0.001") -> bool:
    """회계 정합 동등 비교 — 절대 허용 오차.

    float 의 `math.isclose` 대신 Decimal 기반. 회계 등식 검증 (자산 = 부채 + 자본)
    이나 비율 동등 비교에서 epsilon 흡수.

    Args:
        a, b: 비교 대상.
        absTol: 절대 허용 오차 (기본 0.001).
    Returns:
        bool.
    Example:
        >>> isClose(0.1 + 0.2, 0.3)
        True
        >>> isClose("1000.00", "1000.01", absTol="0.001")
        False
        >>> isClose("1000.00", "1000.01", absTol="0.05")
        True
    """
    da = toDecimal(a, default=Decimal("0"))
    db = toDecimal(b, default=Decimal("0"))
    tol = toDecimal(absTol)
    return abs(da - db) <= tol


def safeDivide(numerator: Any, denominator: Any, *, default: Decimal = Decimal("0")) -> Decimal:
    """0 분모 안전 나눗셈 — 재무비율 계산의 경계 처리 (T10-4).

    Capabilities:
        분모가 0 / None / 변환 실패 시 raise 대신 default 반환. 재무비율 (PBR /
        PER / ROA / ROE / DSCR) 계산의 *0 분모 사고* 차단.

    Args:
        numerator: 분자.
        denominator: 분모.
        default: 분모 0 또는 None 시 반환 (기본 Decimal("0")).

    Returns:
        Decimal.

    Example:
        >>> safeDivide(100, 0)
        Decimal('0')
        >>> safeDivide(100, 0, default=Decimal("NaN"))
        Decimal('NaN')
        >>> safeDivide("100.0", "3.0")
        Decimal('33.33333333333333333333333333')

    Guide:
        Polars DataFrame 안 비율 계산은 별도 패턴 — 본 함수는 *단일 값* 경계.

    SeeAlso:
        toDecimal: 안전 변환.
        roundDecimal: 반올림.
        isClose: 동등 비교.

    Requires:
        Decimal context (prec=28, ROUND_HALF_EVEN, 본 모듈이 자동 설정).

    AIContext:
        T7-4 (회계 정합 트랙) 의 핵심. analysis/ratios / credit/altman 등 재무
        비율 계산의 일관된 경계 처리.

    Raises:
        없음 — 모든 입력 케이스가 default 또는 정상 값으로 처리.
    """
    num = toDecimal(numerator, default=Decimal("0"))
    den = toDecimal(denominator, default=Decimal("0"))
    if den == 0:
        return default
    return num / den


__all__ = ["Decimal", "toDecimal", "roundDecimal", "isClose", "safeDivide"]
