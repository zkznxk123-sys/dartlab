"""CompileFinancialDashboard tool smoke + template 검증.

마스터 플랜 트랙 1 PR-3 동행.
"""

from __future__ import annotations

import pytest

from dartlab.ai.tools import executeTool, listToolNames

pytestmark = pytest.mark.unit


def test_compileFinancialDashboard_registered() -> None:
    assert "CompileFinancialDashboard" in listToolNames()


def test_compileFinancialDashboard_missing_stock_code() -> None:
    result = executeTool("CompileFinancialDashboard", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_compileFinancialDashboard_invalid_stock_code() -> None:
    result = executeTool("CompileFinancialDashboard", {"stockCode": "999999"})
    assert result["ok"] is False
    assert result["error"] == "company_not_resolved"


def test_compileFinancialDashboard_legacy_snake_alias() -> None:
    result = executeTool("compile_financial_dashboard", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_compileFinancialDashboard_default_exposed() -> None:
    """default tool 노출 회귀 가드."""
    from dartlab.ai.agent import _DEFAULT_TOOL_NAMES

    assert "CompileFinancialDashboard" in _DEFAULT_TOOL_NAMES


def test_buildDashboardSpec_growth_template() -> None:
    """growth template — revenue/operatingProfit/netIncome 3 metric."""
    from dartlab.ai.tools.compileFinancialDashboard import _buildDashboardSpec

    metrics = {"revenue": 100.0, "operatingProfit": 20.0, "netIncome": 15.0, "totalAssets": 500.0}
    spec = _buildDashboardSpec("growth", "삼성전자", "005930", metrics)
    assert spec["chartType"] == "bar"
    assert spec["template"] == "growth"
    labels = [d["label"] for d in spec["data"]]
    assert labels == ["revenue", "operatingProfit", "netIncome"]
    # totalAssets 는 growth template 에 없음
    assert "totalAssets" not in labels


def test_buildDashboardSpec_credit_template() -> None:
    """credit template — totalAssets/totalLiabilities/totalEquity/debtRatio."""
    from dartlab.ai.tools.compileFinancialDashboard import _buildDashboardSpec

    metrics = {"totalAssets": 500.0, "totalLiabilities": 200.0, "totalEquity": 300.0, "debtRatio": 66.7, "roe": 5.0}
    spec = _buildDashboardSpec("credit", "test", "A", metrics)
    labels = [d["label"] for d in spec["data"]]
    assert "totalLiabilities" in labels
    assert "debtRatio" in labels
    assert "roe" not in labels


def test_buildDashboardSpec_unknown_template_fallback() -> None:
    """잘못된 template → growth fallback (compileFinancialDashboard 호출 시점에 normalize)."""
    from dartlab.ai.tools.compileFinancialDashboard import _buildDashboardSpec

    spec = _buildDashboardSpec("nonexistent", "x", "Y", {"revenue": 1.0})
    # _buildDashboardSpec 자체는 unknown 도 처리 (growth fallback)
    assert spec["template"] == "nonexistent"  # tag 는 보존, metric set 만 growth 로
    assert any(d["label"] == "revenue" for d in spec["data"])


def test_buildDashboardSpec_skips_none_metrics() -> None:
    """None metric 은 data 에 포함 안 됨."""
    from dartlab.ai.tools.compileFinancialDashboard import _buildDashboardSpec

    metrics = {"revenue": 100.0, "operatingProfit": None, "netIncome": 15.0}
    spec = _buildDashboardSpec("growth", "x", "Y", metrics)
    labels = [d["label"] for d in spec["data"]]
    assert "operatingProfit" not in labels
    assert "revenue" in labels
    assert "netIncome" in labels
