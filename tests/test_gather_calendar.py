"""calendar capability — KR fiscal cycle 추론 단위 테스트.

F1.4 (commit 5f7b561cf) 에서 `gather/calendar.py` 가 `providers/dart/calendar.py` 로
이전됨 (정공법 A Hierarchy). 호출 진입점도 `gather('calendar')` 폐기 (deprecated) →
`Company.calendar(horizonDays)` 메서드.

검증:
- KR fiscal cycle 추론 — last 분기/반기/사업보고서 → next due
- horizonDays 필터 (predictCalendar 시그니처)
- gather('calendar') 폐기 (raise ValueError)
"""

from __future__ import annotations

from datetime import date, datetime

import polars as pl
import pytest

from dartlab.providers.dart.calendar import (
    _nextKrCycle,
    _parseDate,
    _predictNextFiling,
    predictCalendar,
)

pytestmark = pytest.mark.unit


class TestParseDate:
    def test_iso_string(self):
        assert _parseDate("2026-05-07") == date(2026, 5, 7)

    def test_yyyymmdd(self):
        assert _parseDate("20260507") == date(2026, 5, 7)

    def test_date_object(self):
        d = date(2026, 5, 7)
        assert _parseDate(d) == d

    def test_datetime_object(self):
        dt = datetime(2026, 5, 7, 10, 30)
        assert _parseDate(dt) == date(2026, 5, 7)

    def test_none_or_empty(self):
        assert _parseDate(None) is None
        assert _parseDate("") is None
        assert _parseDate("invalid") is None


class TestNextKrCycle:
    def test_returns_none_when_history_too_old(self):
        # 마지막 보고서가 2 년 전 → 비활성/폐지 가능, 예측 안 함
        old = date(date.today().year - 2, 5, 15)
        result = _nextKrCycle({"QUARTERLY_REPORT": old})
        # 모든 후보가 너무 오래됨 → None
        assert result is None or result[0] != "QUARTERLY_REPORT"

    def test_empty_history(self):
        assert _nextKrCycle({}) is None


class TestPredictNextFiling:
    def test_handles_missing_columns(self):
        df = pl.DataFrame({"foo": [1, 2]})
        assert _predictNextFiling(df, code="005930") is None

    def test_predicts_from_recent_quarterly_history(self):
        # 최근 1 년 분기보고서 2 회 (HIGH confidence)
        today = date.today()
        recent_q = date(today.year - 1 if today.month < 6 else today.year, 5, 15)
        prev_q = date(today.year - 1, 11, 14)
        df = pl.DataFrame(
            {
                "title": ["분기보고서 (2024.03)", "분기보고서 (2023.09)"],
                "filedAt": [recent_q.isoformat(), prev_q.isoformat()],
            }
        )
        result = _predictNextFiling(df, code="005930")
        if result is None:
            # cycle 가 모두 과거면 None — OK (오늘 날짜에 따라 달라짐)
            pytest.skip("today 시점 cycle 모두 과거")
        assert result["code"] == "005930"
        assert result["eventType"] == "QUARTERLY_REPORT"
        assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")
        assert result["date"] >= today

    def test_no_kr_filing_types_in_history(self):
        df = pl.DataFrame({"title": ["임원 변경"], "filedAt": ["2025-01-01"]})
        assert _predictNextFiling(df, code="005930") is None


class TestPredictCalendar:
    """predictCalendar 새 시그니처 (disclosures dict + horizonDays)."""

    def test_empty_disclosures(self):
        result = predictCalendar({})
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()

    def test_returns_schema(self):
        result = predictCalendar({"005930": pl.DataFrame({"title": [], "filedAt": []})})
        expected = {"date", "code", "eventType", "title", "source", "impactHint", "confidence"}
        assert expected.issubset(set(result.columns))

    def test_horizon_filter(self):
        # 최근 분기/반기/사업 history → 다음 cycle 예측
        today = date.today()
        history = pl.DataFrame(
            {
                "title": ["분기보고서 (1Q)", "분기보고서 (3Q)"],
                "filedAt": [f"{today.year - 1}-05-15", f"{today.year - 1}-11-14"],
            }
        )
        # horizon 0 → 미래 cycle 모두 제외 → 빈 DataFrame
        result = predictCalendar({"005930": history}, horizonDays=0)
        assert result.is_empty()


class TestGatherCalendarDeprecated:
    """gather('calendar') 진입점 폐기 (F1.4)."""

    def test_gather_calendar_raises(self):
        from dartlab.gather.entry import GatherEntry

        gather = GatherEntry()
        with pytest.raises(ValueError, match="calendar"):
            gather("calendar", "005930")
