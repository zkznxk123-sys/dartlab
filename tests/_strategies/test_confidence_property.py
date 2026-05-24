"""core/confidence hypothesis property — T6-1."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestConfidenceProperty:
    """confidence label / applyVerifyPenalty property 5."""

    @given(c=st.integers(min_value=0, max_value=100))
    def test_label_returns_one_of_three(self, c: int) -> None:
        from dartlab.core.confidence import label

        assert label(c) in {"low", "mid", "high"}

    @given(c=st.integers(min_value=0, max_value=100))
    def test_label_monotone(self, c: int) -> None:
        from dartlab.core.confidence import label

        order = {"low": 0, "mid": 1, "high": 2}
        assert order[label(c)] >= order[label(max(0, c - 50))]

    @given(c=st.integers(min_value=0, max_value=100))
    def test_verify_ok_keeps_score(self, c: int) -> None:
        from dartlab.core.confidence import applyVerifyPenalty

        assert applyVerifyPenalty(c, verifyOk=True) == c

    @given(c=st.integers(min_value=0, max_value=100))
    def test_verify_fail_drops_max_50(self, c: int) -> None:
        from dartlab.core.confidence import applyVerifyPenalty

        result = applyVerifyPenalty(c, verifyOk=False)
        assert result >= 0
        assert result <= c
        assert c - result <= 50

    @given(c=st.integers(min_value=0, max_value=49))
    def test_verify_fail_clamps_at_zero(self, c: int) -> None:
        from dartlab.core.confidence import applyVerifyPenalty

        assert applyVerifyPenalty(c, verifyOk=False) == 0
