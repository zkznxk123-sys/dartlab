"""관세청 series 윈도·집계 회귀 — gather/customs/series.py (네트워크 없음).

월 파싱·1년 윈도 분할·월별 metric 합산(총계행 제외)·stub client 환원.
"""

from __future__ import annotations

import datetime as dt

import pytest

pytestmark = pytest.mark.unit


def test_parseMonth() -> None:
    from dartlab.gather.customs.series import _parseMonth

    assert _parseMonth("2025.10") == dt.date(2025, 10, 1)
    assert _parseMonth("총계") is None
    assert _parseMonth("garbage") is None


def test_monthWindows_splits_by_year() -> None:
    from dartlab.gather.customs.series import _monthWindows

    wins = _monthWindows("202001", "202212", maxMonths=12)
    assert wins == [("202001", "202012"), ("202101", "202112"), ("202201", "202212")]
    assert _monthWindows("202205", "202201") == []
    assert _monthWindows("202203", "202203") == [("202203", "202203")]


def test_aggregateMonthly_excludes_total() -> None:
    from dartlab.gather.customs.series import _aggregateMonthly

    items = [
        {"year": "총계", "expDlr": "150"},
        {"year": "2025.10", "expDlr": "100"},
        {"year": "2025.10", "expDlr": "50"},
    ]
    agg = _aggregateMonthly(items, "expDlr")
    assert agg == {dt.date(2025, 10, 1): 150.0}


class _StubClient:
    def __init__(self, items: list[dict]) -> None:
        self._items = items
        self.calls = 0

    def get(self, hsCode: str, startYm: str, endYm: str, **_: object) -> list[dict]:
        self.calls += 1
        return self._items


def test_fetchSeries_aggregates_and_metric() -> None:
    from dartlab.gather.customs.series import fetchSeries

    items = [
        {"year": "총계", "expDlr": "999", "impDlr": "0", "balPayments": "999"},
        {"year": "2025.10", "expDlr": "100", "impDlr": "40", "balPayments": "60"},
        {"year": "2025.10", "expDlr": "50", "impDlr": "10", "balPayments": "40"},
        {"year": "2025.11", "expDlr": "200", "impDlr": "0", "balPayments": "200"},
    ]
    stub = _StubClient(items)
    df = fetchSeries(stub, "8542", start="2025-10", end="2025-11", metric="expDlr")
    assert df["date"].to_list() == [dt.date(2025, 10, 1), dt.date(2025, 11, 1)]
    assert df["value"].to_list() == [150.0, 200.0]

    bal = fetchSeries(stub, "8542", start="2025-10", end="2025-11", metric="balPayments")
    assert bal["value"].to_list() == [100.0, 200.0]


def test_fetchSeries_invalid_metric() -> None:
    from dartlab.gather.customs.series import fetchSeries

    with pytest.raises(ValueError):
        fetchSeries(_StubClient([]), "8542", metric="nope")


def test_fetchSeries_limit_tail() -> None:
    from dartlab.gather.customs.series import fetchSeries

    items = [
        {"year": "2025.10", "expDlr": "100"},
        {"year": "2025.11", "expDlr": "200"},
        {"year": "2025.12", "expDlr": "300"},
    ]
    df = fetchSeries(_StubClient(items), "8542", start="2025-10", end="2025-12", limit=2)
    assert df["date"].to_list() == [dt.date(2025, 11, 1), dt.date(2025, 12, 1)]
