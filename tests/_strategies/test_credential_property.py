"""core/credentialLifecycle hypothesis property — T6-1 (10/10)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st


@pytest.mark.unit
class TestCredentialProperty:
    """credentialLifecycle property 4."""

    @given(
        key=st.text(min_size=1, max_size=30),
        lifetimeDays=st.integers(min_value=1, max_value=365),
    )
    def test_record_issuance_then_days_until_expiry(self, key: str, lifetimeDays: int) -> None:
        from dartlab.core.credentialLifecycle import daysUntilExpiry, recordIssuance

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.json"
            recordIssuance(key, lifetimeDays=lifetimeDays, path=path)
            days = daysUntilExpiry(key, path=path)
            assert days is not None
            assert lifetimeDays - 2 <= days <= lifetimeDays

    def test_days_until_expiry_missing_returns_none(self) -> None:
        from dartlab.core.credentialLifecycle import daysUntilExpiry

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.json"
            assert daysUntilExpiry("MISSING_KEY", path=path) is None

    @given(lifetimeDays=st.integers(min_value=1, max_value=365))
    def test_check_lifecycle_warning_threshold(self, lifetimeDays: int) -> None:
        from dartlab.core.credentialLifecycle import checkLifecycle, recordIssuance

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.json"
            recordIssuance("TEST_KEY", lifetimeDays=lifetimeDays, path=path)
            alerts = checkLifecycle(thresholdDays=lifetimeDays + 1, path=path)
            assert len(alerts) >= 1
            assert alerts[0].severity in ("warning", "critical", "expired")

    def test_check_lifecycle_empty_returns_empty(self) -> None:
        from dartlab.core.credentialLifecycle import checkLifecycle

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lifecycle.json"
            assert checkLifecycle(path=path) == []
