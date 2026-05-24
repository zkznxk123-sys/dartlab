"""core/logger.logEvent hypothesis property — T6-1."""

from __future__ import annotations

import logging

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


@pytest.mark.unit
class TestLogEventProperty:
    """logEvent 구조화 출력 property 4."""

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event=st.text(min_size=1, max_size=30))
    def test_log_event_does_not_raise(self, event: str, caplog: pytest.LogCaptureFixture) -> None:
        from dartlab.core.logger import logEvent

        with caplog.at_level(logging.INFO):
            logEvent("INFO", event, foo="bar")

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(event=st.text(min_size=1, max_size=20), n=st.integers(min_value=1, max_value=5))
    def test_kwargs_serialize(self, event: str, n: int, caplog: pytest.LogCaptureFixture) -> None:
        from dartlab.core.logger import logEvent

        with caplog.at_level(logging.INFO):
            logEvent("INFO", event, n=n)

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]))
    def test_string_level_accepted(self, level: str, caplog: pytest.LogCaptureFixture) -> None:
        from dartlab.core.logger import logEvent

        with caplog.at_level(logging.DEBUG):
            logEvent(level, "test_event")

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        level=st.sampled_from([logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]),
    )
    def test_int_level_accepted(self, level: int, caplog: pytest.LogCaptureFixture) -> None:
        from dartlab.core.logger import logEvent

        with caplog.at_level(level):
            logEvent(level, "test_event")
