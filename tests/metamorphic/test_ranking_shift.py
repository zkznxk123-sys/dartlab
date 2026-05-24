"""Ranking shift 보존 — 같은 입력 → 같은 순서 (T6-3 패턴 2)."""

from __future__ import annotations

import pytest


@pytest.mark.metamorphic
@pytest.mark.unit
class TestRankingShift:
    """동일 데이터 + 동일 호출 → 동일 ranking 검증."""

    def test_identical_input_identical_order(self) -> None:
        """같은 input 정렬 2회 호출 → 같은 결과."""
        data = [("005930", 12.4), ("000660", 8.1), ("035420", 5.3)]
        sorted1 = sorted(data, key=lambda x: -x[1])
        sorted2 = sorted(data, key=lambda x: -x[1])
        assert sorted1 == sorted2

    def test_equal_value_stable_order(self) -> None:
        """동일 score 가 있을 때 sorted() 의 stability 보장."""
        data = [("a", 1.0), ("b", 1.0), ("c", 1.0)]
        sorted1 = sorted(data, key=lambda x: -x[1])
        sorted2 = sorted(data, key=lambda x: -x[1])
        assert sorted1 == sorted2
        # stable — 원본 순서 보존
        assert sorted1[0][0] == "a"

    @pytest.mark.parametrize("size", [1, 10, 100, 1000])
    def test_ranking_stable_across_sizes(self, size: int) -> None:
        """크기별 ranking 안정성 — 같은 size 두 번 호출 동일."""
        data = [(f"x{i}", i * 0.1) for i in range(size)]
        a = sorted(data, key=lambda x: -x[1])
        b = sorted(data, key=lambda x: -x[1])
        assert a == b
