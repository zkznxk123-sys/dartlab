"""Sentinel — flow 합산 헬퍼 단일 진실의 원천 (Layer 2).

`core/finance/flow.py::annualSumFlow` 가 표준. 4 헬퍼는 모두 위임:
- `analysis/financial/_helpers.py::ttmSum`
- `analysis/financial/_helpers.py::getFlowValue`
- `credit/metrics.py::_ttmSum`
- `review/narrative.py::_annualizeFlow`

같은 입력 같은 출력 검증.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


_PERIODS = ["2025Q1", "2025Q2", "2025Q3", "2025Q4"]
_DATA_FULL = {"2025Q1": 10.0, "2025Q2": 12.0, "2025Q3": 14.0, "2025Q4": 16.0}
_DATA_PARTIAL = {"2025Q1": 10.0, "2025Q2": 12.0, "2025Q3": 14.0}  # Q4 결손
_DATA_FALLBACK = {"2025Q1": None, "2025Q2": None, "2025Q3": None, "2025Q4": 50.0}  # 누적공시 패턴


def test_ttmSum_delegates_to_annualSumFlow():
    from dartlab.analysis.financial._helpers import ttmSum
    from dartlab.core.finance.flow import annualSumFlow

    a = ttmSum(_DATA_FULL, "2025Q4", set(_PERIODS))
    b = annualSumFlow(_DATA_FULL, "2025Q4", set(_PERIODS), withFallback=True)
    assert a == b == 52.0


def test_credit_ttmSum_delegates_to_annualSumFlow():
    from dartlab.core.finance.flow import annualSumFlow
    from dartlab.credit.metrics import _ttmSum

    a = _ttmSum(_DATA_FULL, "2025Q4", _PERIODS)
    b = annualSumFlow(_DATA_FULL, "2025Q4", _PERIODS, withFallback=False)
    assert a == b == 52.0


def test_annualizeFlow_delegates_to_annualizeFlowRows():
    from dartlab.core.finance.flow import annualizeFlowRows
    from dartlab.review.narrative import _annualizeFlow

    rows = {"매출액": _DATA_FULL.copy()}
    a = _annualizeFlow(rows, _PERIODS)
    b = annualizeFlowRows(rows, _PERIODS)
    assert a == b
    assert a["매출액"]["2025Q4"] == 52.0  # Q4 가 연간 합으로 교체됨


def test_ttmSum_fallback_pattern():
    """ttmSum (analysis 모드) 가 누적공시 fallback 인식."""
    from dartlab.analysis.financial._helpers import ttmSum

    # Q1·Q2 None + Q4 단독 → Q4 그대로
    result = ttmSum(_DATA_FALLBACK, "2025Q4", set(_PERIODS))
    assert result == 50.0


def test_credit_ttmSum_no_fallback():
    """credit `_ttmSum` 는 fallback 없이 1~2 분기 부분 합산."""
    from dartlab.credit.metrics import _ttmSum

    # 1 분기만 있는 데이터 → val × 4 (부정확하지만 None 아님)
    data = {"2025Q4": 50.0}
    result = _ttmSum(data, "2025Q4", ["2025Q4"])
    assert result == 200.0  # 50 * 4


def test_getFlowValue_quarterlyMode():
    """getFlowValue: quarterlyMode True → ttmSum 호출, False → 직접 read."""
    from dartlab.analysis.financial._helpers import getFlowValue

    assert getFlowValue(_DATA_FULL, "2025Q4", True, set(_PERIODS)) == 52.0
    assert getFlowValue({"2024": 100}, "2024", False, {"2024"}) == 100
