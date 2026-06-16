"""providers/dart/search/freshness.py mirror tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_freshness_normalizes_dates_and_periods() -> None:
    from dartlab.providers.dart.search.freshness import normalizeSearchDate, periodToDataAsOf, sourceDataAsOfFromRow

    assert normalizeSearchDate("2026-06-16") == "20260616"
    assert periodToDataAsOf("2025Q4") == "20251231"
    assert sourceDataAsOfFromRow({"period": "2026Q1"}) == "20260331"
    assert sourceDataAsOfFromRow({"filing_date": "2025-04-28", "period": "2025Q1"}) == "20250428"
