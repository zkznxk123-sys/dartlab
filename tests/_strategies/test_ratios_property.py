"""core/ratios hypothesis property — T6-1 트랙 (3/5 모듈).

yoyPct / _safeRound 의 property.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests._strategies import ratio_value


@pytest.mark.unit
class TestRatiosProperty:
    """core/ratios 의 5 property."""

    @given(prev=st.floats(min_value=0.01, max_value=1e9, allow_nan=False, allow_infinity=False))
    def test_yoy_pct_zero_change_is_zero(self, prev: float) -> None:
        """전기 = 당기 → 0%."""
        from dartlab.core.ratios import yoyPct

        result = yoyPct(prev, prev)
        if result is not None:
            assert abs(result) < 1e-6

    @given(prev=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False))
    def test_yoy_pct_doubled_is_100(self, prev: float) -> None:
        """당기 = 전기 × 2 → +100%."""
        from dartlab.core.ratios import yoyPct

        result = yoyPct(prev * 2, prev)
        if result is not None:
            assert abs(result - 100.0) < 1e-3

    def test_yoy_pct_zero_prev_returns_none(self) -> None:
        """전기 = 0 → None (보호)."""
        from dartlab.core.ratios import yoyPct

        assert yoyPct(100, 0) is None
        assert yoyPct(-100, 0) is None

    def test_yoy_pct_none_returns_none(self) -> None:
        """입력 None → None."""
        from dartlab.core.ratios import yoyPct

        assert yoyPct(None, 100) is None
        assert yoyPct(100, None) is None

    @given(value=ratio_value, n=st.integers(min_value=0, max_value=8))
    def test_safe_round_returns_float_or_none(self, value: float, n: int) -> None:
        from dartlab.core.ratios import _safeRound

        result = _safeRound(value, n)
        if result is not None:
            assert isinstance(result, float)
