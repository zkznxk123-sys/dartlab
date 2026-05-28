"""RegressionForecast tool smoke + helper 검증.

마스터 플랜 트랙 1 PR-7 동행. 실제 model load 는 ~/.dartlab/regressionModels/ 의존 →
cache 없으면 model_unavailable 예상. helper 결정론 중심.
"""

from __future__ import annotations

import datetime as dt

import pytest

from dartlab.ai.tools import executeTool, listToolNames

pytestmark = pytest.mark.unit


def test_regressionForecast_registered() -> None:
    assert "RegressionForecast" in listToolNames()


def test_regressionForecast_missing_stock_code() -> None:
    result = executeTool("RegressionForecast", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_regressionForecast_invalid_stock_code() -> None:
    result = executeTool("RegressionForecast", {"stockCode": "999999"})
    assert result["ok"] is False
    assert result["error"] in {
        "company_not_resolved",
        "regression_module_unavailable",
        "model_unavailable",
        "model_load_failed",
        "features_unavailable",
        "predict_failed",
    }


def test_regressionForecast_legacy_snake_alias() -> None:
    result = executeTool("regression_forecast", {})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_regressionForecast_default_exposed() -> None:
    """default tool 노출 회귀 가드."""
    from dartlab.ai.agent import _DEFAULT_TOOL_NAMES

    assert "RegressionForecast" in _DEFAULT_TOOL_NAMES


def test_resolveYear_none_returns_last_year() -> None:
    """year=None → 직전 회계연도."""
    from dartlab.ai.tools.regressionForecast import _resolveYear

    now_year = dt.datetime.now(dt.UTC).year
    assert _resolveYear(None) == now_year - 1


def test_resolveYear_explicit_year() -> None:
    """명시 year → 그대로 반환."""
    from dartlab.ai.tools.regressionForecast import _resolveYear

    assert _resolveYear(2023) == 2023
    assert _resolveYear(2020) == 2020


def test_resolveYear_invalid_falls_back() -> None:
    """잘못된 year (< 1900) → 직전 연도 fallback."""
    from dartlab.ai.tools.regressionForecast import _resolveYear

    now_year = dt.datetime.now(dt.UTC).year
    assert _resolveYear(1000) == now_year - 1
    assert _resolveYear(0) == now_year - 1
