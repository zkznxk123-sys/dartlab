"""prompts.matchTriggerHints 단위 테스트 — 마스터 플랜 v2 트랙 6 PR-L2.

system prompt 압축 후 trigger dynamic inline 검증. 외부 호출 0.
"""

from __future__ import annotations

import pytest

from dartlab.ai.workbench.prompts import _TOOL_TRIGGER_HINTS, matchTriggerHints

pytestmark = pytest.mark.unit


def test_matchTriggerHints_dcf_keyword() -> None:
    """DCF / 적정가격 → DCFValuation."""
    hints = matchTriggerHints("삼성전자 적정가격 알려줘")
    assert len(hints) >= 1
    assert hints[0][0] == "DCFValuation(stockCode)"


def test_matchTriggerHints_credit() -> None:
    """신용등급 → CreditScorecard."""
    hints = matchTriggerHints("삼성전자 신용등급")
    assert any("CreditScorecard" in h[0] for h in hints)


def test_matchTriggerHints_sensitivity() -> None:
    """민감도 → SensitivityAnalysis."""
    hints = matchTriggerHints("WACC 민감도 분석")
    assert any("SensitivityAnalysis" in h[0] for h in hints)


def test_matchTriggerHints_scenario_compare() -> None:
    """여러 시나리오 → ScenarioCompareN."""
    hints = matchTriggerHints("여러 시나리오 스트레스 테스트")
    assert any("ScenarioCompareN" in h[0] for h in hints)


def test_matchTriggerHints_dashboard() -> None:
    """대시보드 → CompileFinancialDashboard."""
    hints = matchTriggerHints("삼성전자 한 화면 요약")
    assert any("CompileFinancialDashboard" in h[0] for h in hints)


def test_matchTriggerHints_macro_overlay() -> None:
    """금리 +bp → ScenarioOverlay."""
    hints = matchTriggerHints("금리 +50bp 시 삼성전자 영향")
    assert any("ScenarioOverlay" in h[0] for h in hints)


def test_matchTriggerHints_unrelated_returns_empty() -> None:
    """trigger 없는 질문 → 빈 list."""
    assert matchTriggerHints("안녕하세요") == []
    assert matchTriggerHints("") == []
    assert matchTriggerHints("오늘 날씨") == []


def test_matchTriggerHints_dedup_same_tool() -> None:
    """같은 도구 매칭 trigger 여러 개 → 도구 1 번만 반환."""
    # DCFValuation 의 trigger 여러 개 동시 매칭
    hints = matchTriggerHints("DCF 적정가격 내재가치 평가")
    dcf_hits = [h for h in hints if "DCFValuation" in h[0]]
    assert len(dcf_hits) == 1


def test_matchTriggerHints_multiple_tools() -> None:
    """다른 도구 매칭 → 각각 1 번씩."""
    hints = matchTriggerHints("삼성전자 DCF 적정가격 + WACC 민감도 + 신용등급")
    tool_names = [h[0].split("(")[0] for h in hints]
    assert "DCFValuation" in tool_names
    assert "SensitivityAnalysis" in tool_names
    assert "CreditScorecard" in tool_names


def test_trigger_hints_dataset_well_formed() -> None:
    """_TOOL_TRIGGER_HINTS 형식 — (triggers tuple, toolSig, hint) tuple."""
    assert len(_TOOL_TRIGGER_HINTS) == 8
    for entry in _TOOL_TRIGGER_HINTS:
        triggers, toolSig, hint = entry
        assert isinstance(triggers, tuple)
        assert len(triggers) >= 1
        assert isinstance(toolSig, str) and "(" in toolSig
        assert isinstance(hint, str) and hint
