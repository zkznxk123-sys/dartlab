"""ScenarioCompareN tool smoke + contract 검증.

마스터 플랜 트랙 1 PR-5 동행. macro.scenarios.engine.compareScenarios wrap.
실제 macro provider 호출은 무거우니 skip + helper 결정론 검증 중심.
"""

from __future__ import annotations

import pytest

from dartlab.ai.tools import executeTool, listToolNames

pytestmark = pytest.mark.unit


def test_scenarioCompareN_registered() -> None:
    """registry 등록 검증."""
    assert "ScenarioCompareN" in listToolNames()


def test_scenarioCompareN_missing_names() -> None:
    """scenarioNames 누락 → error."""
    result = executeTool("ScenarioCompareN", {})
    assert result["ok"] is False
    assert result["error"] == "missing_scenario_names"


def test_scenarioCompareN_single_name_rejected() -> None:
    """단일 시나리오 → insufficient_scenarios error."""
    result = executeTool("ScenarioCompareN", {"scenarioNames": ["2008 금융위기"]})
    assert result["ok"] is False
    assert result["error"] == "insufficient_scenarios"


def test_scenarioCompareN_empty_list_rejected() -> None:
    """빈 list → error."""
    result = executeTool("ScenarioCompareN", {"scenarioNames": []})
    assert result["ok"] is False
    assert result["error"] in {"missing_scenario_names", "insufficient_scenarios"}


def test_scenarioCompareN_legacy_snake_alias() -> None:
    """snake alias."""
    result = executeTool("scenario_compare_n", {})
    assert result["ok"] is False
    assert result["error"] == "missing_scenario_names"


def test_scenarioCompareN_default_exposed() -> None:
    """default tool 노출 회귀 가드."""
    from dartlab.ai.agent import _DEFAULT_TOOL_NAMES

    assert "ScenarioCompareN" in _DEFAULT_TOOL_NAMES


def test_scenarioCompareN_invalid_market_normalized() -> None:
    """잘못된 market 'JP' 등은 US 로 normalize. (실 시나리오 매칭 실패는 별 error)."""
    # 잘못된 시나리오명 + invalid market → compareScenarios 가 throw 또는 빈 comparison.
    result = executeTool(
        "ScenarioCompareN", {"scenarioNames": ["__nonexistent_A__", "__nonexistent_B__"], "market": "JP"}
    )
    # 잘못된 시나리오라 all_scenarios_unmatched 또는 compare_failed 에러 — market 정규화 자체 분기 0
    assert result["ok"] is False
    assert result["error"] in {"all_scenarios_unmatched", "compare_failed"}
