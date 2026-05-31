"""core/panel period (S2) mirror — 12월결산화 순수 변환 (데이터 0).

``core/panel/period.py`` 의 ``periodFromEnd``/``isPeriodColumn``/``sortPeriods`` 검증.
결산월 무관 달력월 매핑 + 1~2월 직전년도 Q4 (12월결산 양식).
"""

from __future__ import annotations

import pytest

from dartlab.providers.dart.panel._period import isPeriodColumn, periodFromEnd, sortPeriods

pytestmark = pytest.mark.unit


def test_period_from_end_calendar_quarter() -> None:
    """보고기간 종료 (year, month) → YYYYQn (달력월, 1~2월=직전년도 Q4)."""
    assert periodFromEnd(2024, 9) == "2024Q3"
    assert periodFromEnd(2024, 12) == "2024Q4"
    assert periodFromEnd(2024, 3) == "2024Q1"
    assert periodFromEnd(2024, 1) == "2023Q4"
    assert periodFromEnd(2024, 2) == "2023Q4"


def test_is_period_column() -> None:
    """YYYYQn 형식만 period 열로 판정."""
    assert isPeriodColumn("2024Q3")
    assert not isPeriodColumn("chapter")
    assert not isPeriodColumn("disclosureKey")


def test_sort_periods_ascending() -> None:
    """period 키 오름차순 정렬."""
    out = sortPeriods(["2024Q4", "2023Q1", "2024Q1"])
    assert out == ["2023Q1", "2024Q1", "2024Q4"]
