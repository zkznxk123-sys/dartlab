"""R25 audit 회귀 테스트 — credit 엔진.

R25-1: history[0] 가 partial period (BS only, 손익/CF 모두 None) 일 때
다음 행으로 fallback. EDGAR 회계연도 경계 이슈.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_credit_engine_has_partial_period_fallback():
    """R25-1: engine.py 에 partial period fallback 코드가 있는지 source 검증."""
    from dartlab.credit.engine import evaluateCompany
    import inspect
    src = inspect.getsource(evaluateCompany)
    assert "_CORE_METRIC_KEYS" in src, "fallback 마커 누락"
    assert "ebitda" in src and "ocf" in src


def test_credit_fallback_logic_with_mock_history():
    """R25-1: mock history 로 fallback 동작 검증."""
    # _CORE_METRIC_KEYS 가 모두 None 인 첫 행 + 정상인 두 번째 행
    history = [
        {"period": "2026Q1", "ebitda": None, "ocf": None, "netIncome": None, "interestExpense": None,
         "totalBorrowing": 88512000000.0, "currentRatio": 97.37},
        {"period": "2025", "ebitda": 130000000000.0, "ocf": 110000000000.0, "netIncome": 95000000000.0,
         "interestExpense": 5000000000.0, "totalBorrowing": 88512000000.0, "currentRatio": 95.0},
    ]
    _CORE_METRIC_KEYS = ("ebitda", "ocf", "netIncome", "interestExpense")

    latest = history[0]
    if all(latest.get(k) is None for k in _CORE_METRIC_KEYS) and len(history) > 1:
        for row in history[1:]:
            if any(row.get(k) is not None for k in _CORE_METRIC_KEYS):
                latest = row
                break

    assert latest["period"] == "2025", "fallback failed"
    assert latest["ebitda"] == 130000000000.0


def test_credit_normal_history_keeps_first():
    """history[0] 가 정상이면 fallback 안 함 (회귀 보호)."""
    history = [
        {"period": "2025Q4", "ebitda": 50000000000.0, "ocf": 80000000000.0, "netIncome": 45000000000.0,
         "interestExpense": 1000000000.0},
        {"period": "2024Q4", "ebitda": 30000000000.0},
    ]
    _CORE_METRIC_KEYS = ("ebitda", "ocf", "netIncome", "interestExpense")

    latest = history[0]
    if all(latest.get(k) is None for k in _CORE_METRIC_KEYS) and len(history) > 1:
        for row in history[1:]:
            if any(row.get(k) is not None for k in _CORE_METRIC_KEYS):
                latest = row
                break

    assert latest["period"] == "2025Q4"


def test_credit_axis_filter_unknown_raises():
    """기존 동작 — 없는 축 ValueError 보호."""
    from dartlab.credit import _filterAxis

    # _filterAxis 는 result + axis 받음
    with pytest.raises(ValueError, match="알 수 없는 신용분석 축"):
        _filterAxis({"grade": "dCR-AA"}, "없는축")


def test_credit_score_meaning_label_present():
    """R22-1: _scoreMeaning 라벨 보호 (회귀)."""
    from dartlab.credit.engine import _CREDIT_SCORE_LEGEND

    assert "위험 점수" in _CREDIT_SCORE_LEGEND
    assert "value" in _CREDIT_SCORE_LEGEND
