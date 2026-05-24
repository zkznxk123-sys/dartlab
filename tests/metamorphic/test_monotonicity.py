"""Monotonicity — 단조 입력 → 단조 출력 (T6-3 패턴 4)."""

from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.metamorphic
@pytest.mark.unit
class TestMonotonicity:
    """수치 함수의 단조 성질 검증 (입력 ↑ → 출력 ↑ 또는 ↓)."""

    def test_safe_divide_monotonic_in_numerator(self) -> None:
        """safeDivide(N, D) 의 N 증가 → 결과 증가 (D > 0)."""
        from dartlab.core.decimal import safeDivide

        d = Decimal("10")
        a = safeDivide(100, d)
        b = safeDivide(200, d)
        c = safeDivide(300, d)
        assert a < b < c

    def test_safe_divide_anti_monotonic_in_denominator(self) -> None:
        """safeDivide(N, D) 의 D 증가 → 결과 감소 (N > 0)."""
        from dartlab.core.decimal import safeDivide

        n = Decimal("100")
        a = safeDivide(n, 1)
        b = safeDivide(n, 10)
        c = safeDivide(n, 100)
        assert a > b > c

    @pytest.mark.parametrize(
        ("low", "mid", "high"),
        [(1, 5, 10), (100, 500, 1000), (0.1, 0.5, 1.0)],
    )
    def test_round_decimal_monotonic(self, low: float, mid: float, high: float) -> None:
        """roundDecimal 단조 성질 (반올림 후에도 순서 유지)."""
        from dartlab.core.decimal import roundDecimal

        a = roundDecimal(low, places=2)
        b = roundDecimal(mid, places=2)
        c = roundDecimal(high, places=2)
        assert a <= b <= c
