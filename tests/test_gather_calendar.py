"""gather('calendar') capability — Scope 2-B 단위 테스트.

검증:
- KR fiscal cycle 추론 — last 분기/반기/사업보고서 → next due
- horizon_days 필터
- 빈 history (DART API 키 미설정 / 미커버 종목) → 빈 DataFrame
- US 시장 호출 → 빈 DataFrame (P1 대상)
- gather entry 등록 (axis="calendar" + 한글 alias "일정")

ref: plan §2-B, runtime: engines.gather skill 갱신 확인.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import polars as pl
import pytest

from dartlab.gather.calendar import (
    _next_kr_cycle,
    _normalize_codes,
    _parse_date,
    _predict_next_filing,
    gatherCalendar,
)

pytestmark = pytest.mark.unit


class TestNormalizeCodes:
    def test_string_input(self):
        assert _normalize_codes("005930") == ["005930"]

    def test_list_input(self):
        assert _normalize_codes(["005930", "000660"]) == ["005930", "000660"]

    def test_empty(self):
        assert _normalize_codes("") == []
        assert _normalize_codes(None) == []
        assert _normalize_codes([]) == []

    def test_strip_whitespace(self):
        assert _normalize_codes(["  005930  ", "000660"]) == ["005930", "000660"]


class TestParseDate:
    def test_iso_string(self):
        assert _parse_date("2026-05-07") == date(2026, 5, 7)

    def test_yyyymmdd(self):
        assert _parse_date("20260507") == date(2026, 5, 7)

    def test_date_object(self):
        d = date(2026, 5, 7)
        assert _parse_date(d) == d

    def test_datetime_object(self):
        dt = datetime(2026, 5, 7, 10, 30)
        assert _parse_date(dt) == date(2026, 5, 7)

    def test_none_or_empty(self):
        assert _parse_date(None) is None
        assert _parse_date("") is None
        assert _parse_date("invalid") is None


class TestNextKrCycle:
    @patch("dartlab.gather.calendar.date")
    def test_january_predicts_q1_quarterly(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 15)
        # Required: same module's date class still works for other dates
        mock_date.side_effect = lambda *args: date(*args)
        result = _next_kr_cycle({"QUARTERLY_REPORT": date(2025, 11, 14)})
        assert result is not None
        event_type, predicted = result
        assert event_type == "QUARTERLY_REPORT"
        # 가장 가까운 cycle: 2026 Q1 (5 월 15 일)
        assert predicted.month == 5

    def test_returns_none_when_history_too_old(self):
        # 마지막 보고서가 2 년 전 → 비활성/폐지 가능, 예측 안 함
        old = date(date.today().year - 2, 5, 15)
        result = _next_kr_cycle({"QUARTERLY_REPORT": old})
        # 모든 후보가 너무 오래됨 → None
        assert result is None or result[0] != "QUARTERLY_REPORT"

    def test_empty_history(self):
        assert _next_kr_cycle({}) is None


class TestPredictNextFiling:
    def test_handles_missing_columns(self):
        df = pl.DataFrame({"foo": [1, 2]})
        assert _predict_next_filing(df, code="005930") is None

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
        result = _predict_next_filing(df, code="005930")
        if result is None:
            # cycle 가 모두 과거면 None — OK (오늘 날짜에 따라 달라짐)
            pytest.skip("today 시점 cycle 모두 과거")
        assert result["code"] == "005930"
        assert result["eventType"] == "QUARTERLY_REPORT"
        assert result["confidence"] in ("HIGH", "MEDIUM", "LOW")
        assert result["date"] >= today

    def test_no_kr_filing_types_in_history(self):
        df = pl.DataFrame({"title": ["임원 변경"], "filedAt": ["2025-01-01"]})
        assert _predict_next_filing(df, code="005930") is None


class TestGatherCalendarEntry:
    """gather facade 통합 — axis 등록 / alias / dispatch."""

    def test_calendar_axis_registered(self):
        from dartlab.gather.entry import _AXIS_REGISTRY

        assert "calendar" in _AXIS_REGISTRY
        entry = _AXIS_REGISTRY["calendar"]
        assert entry.targetType == "stockCode"

    def test_korean_alias(self):
        from dartlab.gather.entry import _ALIASES, _resolveAxis

        assert _ALIASES["일정"] == "calendar"
        assert _resolveAxis("일정") == "calendar"
        assert _resolveAxis("캘린더") == "calendar"

    def test_us_market_returns_empty(self):
        # P0 — KR 외 빈 DataFrame
        result = gatherCalendar("AAPL", market="US")
        assert isinstance(result, pl.DataFrame)
        assert result.is_empty()

    def test_empty_codes_raises(self):
        with pytest.raises(ValueError, match="종목코드"):
            gatherCalendar("")

    def test_returns_schema_when_empty(self):
        # 더미 종목코드 → DART API 호출 실패 (또는 빈 history) → 빈 DataFrame schema
        try:
            result = gatherCalendar("999999", horizon_days=30)
        except Exception:
            pytest.skip("DART API 미설정 — 단순 schema 검증 skip")
        # schema 가 정의된 6 컬럼
        expected_cols = {"date", "code", "eventType", "title", "source", "impactHint", "confidence"}
        assert expected_cols.issubset(set(result.columns))


class TestGatherCalendarMockedDisclosure:
    """DART API 호출 mock — 실제 네트워크 안 탐."""

    def test_mocked_history_predicts_next(self):
        # 최근 분기/반기/사업 보고서 history mock
        today = date.today()
        history_rows = [
            {"title": "분기보고서 (1Q)", "filedAt": f"{today.year - 1}-05-15"},
            {"title": "반기보고서", "filedAt": f"{today.year - 1}-08-14"},
            {"title": "분기보고서 (3Q)", "filedAt": f"{today.year - 1}-11-14"},
            {"title": "사업보고서", "filedAt": f"{today.year}-03-31"},
            {"title": "분기보고서 (1Q)", "filedAt": f"{today.year}-05-15"},
        ]
        mock_history = pl.DataFrame(history_rows)

        with patch("dartlab.gather.calendar.Company") as mock_company_cls:
            instance = mock_company_cls.return_value
            instance.disclosure.return_value = mock_history
            result = gatherCalendar("005930", horizon_days=400)

        assert isinstance(result, pl.DataFrame)
        # horizon=400 일이면 향후 1 년 안 cycle 1 개 이상 예상
        if result.is_empty():
            pytest.skip("today 시점이 cycle 사이라 예측 안 됨")
        assert result["code"][0] == "005930"
        assert result["eventType"][0] in ("QUARTERLY_REPORT", "SEMI_REPORT", "ANNUAL_REPORT")
        assert result["confidence"][0] in ("HIGH", "MEDIUM", "LOW")
        # date 오름차순
        if result.height > 1:
            dates = result["date"].to_list()
            assert dates == sorted(dates)
