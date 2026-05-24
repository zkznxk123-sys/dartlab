"""Commutativity — 인자 순서 무관 결과 동일 (T6-3 패턴 5)."""

from __future__ import annotations

import pytest


@pytest.mark.metamorphic
@pytest.mark.unit
class TestCommutativity:
    """symmetric 함수의 인자 순서 독립 검증."""

    def test_addition_commutative(self) -> None:
        """덧셈 — 항등."""
        a, b = 5, 7
        assert a + b == b + a

    def test_multiplication_commutative(self) -> None:
        """곱셈."""
        a, b = 3.14, 2.71
        assert a * b == b * a

    def test_isclose_commutative(self) -> None:
        """core/decimal.isClose 의 a, b 순서 무관."""
        from dartlab.core.decimal import isClose

        assert isClose(1.0, 1.0001, absTol="0.001") == isClose(1.0001, 1.0, absTol="0.001")

    @pytest.mark.parametrize(
        ("a", "b"),
        [(1, 2), (100, 200), (0.5, 1.5), (-3, 7)],
    )
    def test_isclose_commutative_parametric(self, a: float, b: float) -> None:
        """다양한 (a, b) 쌍에서 isClose 대칭성."""
        from dartlab.core.decimal import isClose

        assert isClose(a, b) == isClose(b, a)
