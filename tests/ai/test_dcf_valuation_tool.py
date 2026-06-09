"""DCFValuation tool smoke + contract 검증.

마스터 플랜 트랙 1 PR-1 동행 단위 테스트. dartlab 데이터 의존 무거운 경로는 patch 로 분리.

검증 영역:
1. registry 등록 (executeTool 진입 + listToolNames 노출)
2. stockCode 누락 → missing_stock_code error
3. company_not_resolved (잘못된 코드) → company_not_resolved error
4. _scenarioDict / _safeBaseScore helper 결정론
5. legacy snake_case 매핑 (dcf_valuation → DCFValuation)
6. default tool 노출 (_DEFAULT_TOOL_NAMES) 회귀 가드 (2026-05-17 default 미노출 패턴)
"""

from __future__ import annotations

import pytest

from dartlab.ai.tools import executeTool, listToolNames

pytestmark = pytest.mark.unit


def test_dcfValuation_registered() -> None:
    """registry 등록 검증 — 마스터 플랜 트랙 1 PR-1."""
    assert "DCFValuation" in listToolNames()


def test_dcfValuation_missing_stock_code() -> None:
    """stockCode 빈 입력 → missing_stock_code error."""
    result = executeTool("DCFValuation", {"stockCode": ""})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_dcfValuation_invalid_stock_code() -> None:
    """잘못된 stockCode → company_not_resolved (Company 생성 실패)."""
    result = executeTool("DCFValuation", {"stockCode": "999999"})
    assert result["ok"] is False
    assert result["error"] in {"company_not_resolved", "series_unavailable", "dcf_all_failed"}


def test_dcfValuation_legacy_snake_alias() -> None:
    """legacy snake_case 매핑 — dcf_valuation → DCFValuation."""
    result = executeTool("dcf_valuation", {"stockCode": ""})
    assert result["ok"] is False
    assert result["error"] == "missing_stock_code"


def test_dcfValuation_default_exposed_to_llm() -> None:
    """default tool 노출 회귀 가드.

    옛 도구가 registry 등록만 됐다가 default 미노출이라 LLM 호출 0 회 회귀
    (2026-05-17 OAuth probe). 본 검증으로 DCFValuation 도 동일 회귀 차단.
    """
    from dartlab.ai.agent import _DEFAULT_TOOL_NAMES

    assert "DCFValuation" in _DEFAULT_TOOL_NAMES


def test_dcfValuation_scenarioDict_helper_keys() -> None:
    """_scenarioDict — DCFResult 의 핵심 8 키 보존."""
    from dartlab.ai.tools.dcfValuationTool import _scenarioDict

    class FakeDcf:
        discountRate = 10.0
        growthRateInitial = 5.0
        terminalGrowth = 2.5
        enterpriseValue = 1_000_000.0
        equityValue = 800_000.0
        perShareValue = 80_000.0
        marginOfSafety = 5.5

    out = _scenarioDict(FakeDcf(), "base")
    assert out["scenario"] == "base"
    assert out["perShareValue"] == 80_000.0
    assert out["marginOfSafety"] == 5.5
    assert set(out) == {
        "scenario",
        "discountRate",
        "growthRateInitial",
        "terminalGrowth",
        "enterpriseValue",
        "equityValue",
        "perShareValue",
        "marginOfSafety",
    }


def test_dcfValuation_confidence_uses_forecast_method() -> None:
    """SSOT — DCF confidence 는 core/confidence.py 의 ``forecast`` (30) 사용.

    "dcf" 는 forecast subtype — confidenceMethod 라벨에만 노출, 점수는 30.
    """
    from dartlab.core.confidence import baseScore

    assert baseScore("forecast") == 30
