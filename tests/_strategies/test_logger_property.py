"""core/logger hypothesis property — T6-1 트랙 (6/10 모듈)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestLoggerProperty:
    """core/logger.logEvent property 4."""

    @given(
        event=st.text(alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")), min_size=1, max_size=30)
    )
    def test_log_event_accepts_snake_case(self, event: str) -> None:
        """snake_case event 이름 → 정상 호출 (raise X)."""
        from dartlab.core.logger import logEvent

        logEvent("info", event)

    @given(level=st.sampled_from(["debug", "info", "warning", "warn", "error", "critical"]))
    def test_log_event_accepts_all_levels(self, level: str) -> None:
        """모든 level string 정상 호출."""
        from dartlab.core.logger import logEvent

        logEvent(level, "test_event")

    def test_log_event_invalid_level_raises(self) -> None:
        """unknown level → ValueError."""
        from dartlab.core.logger import logEvent

        with pytest.raises(ValueError, match="unknown level"):
            logEvent("invalid_level_xyz", "test")

    @given(
        fields=st.dictionaries(
            st.text(alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")), min_size=1, max_size=10),
            st.one_of(st.integers(), st.text(max_size=20), st.booleans()),
            min_size=0,
            max_size=5,
        )
    )
    def test_log_event_accepts_arbitrary_fields(self, fields: dict) -> None:
        """임의 dict fields → 정상 호출."""
        from dartlab.core.logger import logEvent

        logEvent("info", "test_event", **fields)
