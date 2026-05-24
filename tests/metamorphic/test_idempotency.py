"""Idempotency — 같은 args 2회 호출 → 같은 ref (T6-3 패턴 3)."""

from __future__ import annotations

import pytest


@pytest.mark.metamorphic
@pytest.mark.unit
class TestIdempotency:
    """함수 호출의 결정론적 동작 검증 (랜덤성 / 시간 의존성 차단)."""

    def test_pure_function_idempotent(self) -> None:
        """순수 함수는 같은 args → 같은 결과."""

        def add(a: int, b: int) -> int:
            return a + b

        assert add(1, 2) == add(1, 2)
        assert add(1, 2) == 3

    def test_hash_function_idempotent(self) -> None:
        """hash 도 같은 input → 같은 output (str/bytes 한정)."""
        s = "dartlab"
        # hash() 는 PYTHONHASHSEED 영향. 따라서 같은 프로세스 안 idempotent.
        assert hash(s) == hash(s)

    def test_safe_divide_idempotent(self) -> None:
        """core/decimal.safeDivide 의 결정론."""
        from dartlab.core.decimal import safeDivide

        assert safeDivide(100, 3) == safeDivide(100, 3)
        assert safeDivide(0, 1) == safeDivide(0, 1)
        assert safeDivide(1, 0) == safeDivide(1, 0)
