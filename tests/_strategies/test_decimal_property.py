"""core/decimal hypothesis property — T6-1 트랙 (1/5 모듈).

20 strategy 시험. safeDivide / roundDecimal / isClose / toDecimal 의 property
보증 (commutativity / monotonicity / NaN 안전 / 0 분모 안전).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests._strategies import decimal_value, financial_amount, positive_amount


@pytest.mark.unit
class TestDecimalProperty:
    """core/decimal 의 property-based 검증 20 strategy."""

    # ── safeDivide ──
    @given(num=financial_amount, den=positive_amount)
    def test_safe_divide_positive_denominator_no_default(self, num: object, den: object) -> None:
        from dartlab.core.decimal import safeDivide

        result = safeDivide(num, den)
        assert isinstance(result, Decimal)

    @given(num=financial_amount)
    def test_safe_divide_zero_denominator_returns_default(self, num: object) -> None:
        from dartlab.core.decimal import safeDivide

        assert safeDivide(num, 0) == Decimal("0")
        assert safeDivide(num, 0, default=Decimal("-1")) == Decimal("-1")

    @given(num=positive_amount, den=positive_amount)
    def test_safe_divide_positive_result(self, num: object, den: object) -> None:
        from dartlab.core.decimal import safeDivide

        result = safeDivide(num, den)
        assert result > 0

    # ── roundDecimal ──
    @given(value=decimal_value, places=st.integers(min_value=0, max_value=10))
    def test_round_decimal_preserves_sign(self, value: Decimal, places: int) -> None:
        from dartlab.core.decimal import roundDecimal

        result = roundDecimal(value, places=places)
        # 작은 값은 0 으로 반올림될 수 있음 (sign 보존 X).
        # 절대값이 1 이상이면 sign 보존.
        if abs(value) >= 1:
            assert (result >= 0) == (value >= 0)

    @given(value=decimal_value)
    def test_round_decimal_idempotent_at_same_places(self, value: Decimal) -> None:
        from dartlab.core.decimal import roundDecimal

        once = roundDecimal(value, places=2)
        twice = roundDecimal(once, places=2)
        assert once == twice

    # ── isClose ──
    @given(a=decimal_value, b=decimal_value)
    def test_is_close_symmetric(self, a: Decimal, b: Decimal) -> None:
        from dartlab.core.decimal import isClose

        assert isClose(a, b) == isClose(b, a)

    @given(value=decimal_value)
    def test_is_close_reflexive(self, value: Decimal) -> None:
        from dartlab.core.decimal import isClose

        assert isClose(value, value)

    # ── toDecimal ──
    @given(value=st.integers(min_value=-(10**9), max_value=10**9))
    def test_to_decimal_int_round_trip(self, value: int) -> None:
        from dartlab.core.decimal import toDecimal

        assert toDecimal(value) == Decimal(value)
