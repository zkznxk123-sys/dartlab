"""Sentinel — flow 합산 헬퍼 단일 진실의 원천.

`core/finance/flow.py::annualSumFlow` 가 표준. credit `_ttmSum` 만 위임 유지
(분기 부족 모드 — credit 안정성 보수). 나머지 헬퍼 (ttmSum/getFlowValue/
_annualizeFlow) 는 Plan v4 에서 제거됨 — pivot annual 컬럼 자동 노출이 흡수.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


_PERIODS = ["2025Q1", "2025Q2", "2025Q3", "2025Q4"]
_DATA_FULL = {"2025Q1": 10.0, "2025Q2": 12.0, "2025Q3": 14.0, "2025Q4": 16.0}
_DATA_PARTIAL = {"2025Q1": 10.0, "2025Q2": 12.0, "2025Q3": 14.0}  # Q4 결손
_DATA_FALLBACK = {"2025Q1": None, "2025Q2": None, "2025Q3": None, "2025Q4": 50.0}  # 누적공시 패턴


def test_annualSumFlow_basic():
    """표준 헬퍼: 4분기 단순 합."""
    from dartlab.core.utils.flow import annualSumFlow

    assert annualSumFlow(_DATA_FULL, "2025Q4", set(_PERIODS), withFallback=True) == 52.0
    assert annualSumFlow(_DATA_FULL, "2025Q4", set(_PERIODS), withFallback=False) == 52.0


def test_annualSumFlow_fallback_pattern():
    """analysis 모드 (withFallback=True) 누적공시 fallback."""
    from dartlab.core.utils.flow import annualSumFlow

    result = annualSumFlow(_DATA_FALLBACK, "2025Q4", set(_PERIODS), withFallback=True)
    assert result == 50.0


def test_annualSumFlow_credit_partial():
    """credit 모드 (withFallback=False): 1~2 분기 부분 합산."""
    from dartlab.core.utils.flow import annualSumFlow

    data = {"2025Q4": 50.0}
    result = annualSumFlow(data, "2025Q4", ["2025Q4"], withFallback=False)
    assert result == 200.0  # 50 * 4 (부정확)


def test_credit_ttmSum_delegates_to_annualSumFlow():
    """credit `_ttmSum` 가 annualSumFlow 위임."""
    from dartlab.core.utils.flow import annualSumFlow
    from dartlab.credit.metrics import _ttmSum

    a = _ttmSum(_DATA_FULL, "2025Q4", _PERIODS)
    b = annualSumFlow(_DATA_FULL, "2025Q4", _PERIODS, withFallback=False)
    assert a == b == 52.0


def test_no_legacy_helper_imports():
    """Plan v4/v5: legacy 헬퍼 모두 제거됨.

    - ttmSum/getFlowValue/isQuarterlyFallback (Plan v4 P3 후속)
    - annualizeFlowRows (Plan v5 F)
    """
    import dartlab.analysis.financial._helpers as h
    import dartlab.core.utils.flow as f

    assert not hasattr(h, "ttmSum"), "ttmSum 은 Plan v4 에서 제거됨"
    assert not hasattr(h, "getFlowValue"), "getFlowValue 는 Plan v4 에서 제거됨"
    assert not hasattr(h, "isQuarterlyFallback"), "isQuarterlyFallback 는 Plan v4 에서 제거됨"
    assert not hasattr(f, "annualizeFlowRows"), "annualizeFlowRows 는 Plan v5 F 에서 제거됨"
