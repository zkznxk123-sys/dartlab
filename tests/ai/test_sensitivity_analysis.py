"""SensitivityAnalysis tool smoke + grid 결정론 검증.

마스터 플랜 트랙 1 PR-4 동행.
"""

from __future__ import annotations

import pytest

from dartlab.ai.tools import executeTool, listToolNames

pytestmark = pytest.mark.unit


def test_sensitivityAnalysis_registered() -> None:
    """registry 등록."""
    assert "SensitivityAnalysis" in listToolNames()


def test_sensitivityAnalysis_missing_stock_code() -> None:
    result = executeTool("SensitivityAnalysis", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_sensitivityAnalysis_invalid_stock_code() -> None:
    """잘못된 종목 → 후속 분기 error."""
    result = executeTool("SensitivityAnalysis", {"stockCode": "999999"})
    assert result["ok"] is False
    assert result["error"] in {
        "company_not_resolved",
        "series_unavailable",
        "base_fcf_failed",
        "non_positive_fcf",
    }


def test_sensitivityAnalysis_legacy_snake_alias() -> None:
    result = executeTool("sensitivity_analysis", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_sensitivityAnalysis_default_exposed() -> None:
    """default tool 노출 회귀 가드."""
    from dartlab.ai.agent import _DEFAULT_TOOL_NAMES

    assert "SensitivityAnalysis" in _DEFAULT_TOOL_NAMES


def test_buildAxisValues_linear() -> None:
    """linear 격자 생성."""
    from dartlab.ai.tools.sensitivityAnalysis import _buildAxisValues

    assert _buildAxisValues(8.0, 12.0, 5) == [8.0, 9.0, 10.0, 11.0, 12.0]
    # steps=1 → single value
    assert _buildAxisValues(10.0, 12.0, 1) == [10.0]
    # steps=2 → 양 끝
    assert _buildAxisValues(0.0, 10.0, 2) == [0.0, 10.0]


def test_buildAxisValues_zero_or_negative_steps() -> None:
    """steps ≤ 1 → low 단일."""
    from dartlab.ai.tools.sensitivityAnalysis import _buildAxisValues

    assert _buildAxisValues(5.0, 10.0, 0) == [5.0]
    assert _buildAxisValues(5.0, 10.0, -3) == [5.0]
