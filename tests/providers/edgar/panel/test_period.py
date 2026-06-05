"""EDGAR panel period facade — DART period 계약 mirror."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_period_facade_matches_dart() -> None:
    from dartlab.providers.edgar.panel.period import isPeriodColumn, periodFromEnd, sortPeriods

    assert periodFromEnd(2024, 12) == "2024Q4"
    assert periodFromEnd(2025, 1) == "2024Q4"
    assert isPeriodColumn("2024Q4")
    assert not isPeriodColumn("2024")
    assert sortPeriods(["2024Q1", "2023Q4"], descending=True) == ["2024Q1", "2023Q4"]
