"""ThemeExposure 도구 — 근거투명 테마 노출 round-trip + 정직 분기.

graph 회귀 가드: 도구 추가만, agent 본체 무변(checkAgentBoundary 별도 audit).
"""

from __future__ import annotations

import pytest

from dartlab.ai.tools.themeTool import themeTool


def test_theme_tool_registered():
    """ThemeExposure 가 registry _SPECS·_TOOLS 양쪽 등록."""
    from dartlab.ai.tools import registry as rg

    assert "ThemeExposure" in rg._SPECS
    assert "ThemeExposure" in rg._TOOLS
    assert rg._SPECS["ThemeExposure"].readOnlyHint is True


@pytest.mark.requires_data
def test_theme_tool_stock_dossier():
    """stockCode 모드 — 소속 테마 + 근거 + 노출%(정직 분기). 허울 정정 가드."""
    # LG화학 → 2차전지 graded 노출%. (도구는 엔진 verb 한국어 컬럼 그대로 노출)
    lg = themeTool(stockCode="051910")
    assert lg.ok
    bat = next(t for t in lg.data["themes"] if t["themeId"] == "secondaryBattery")
    assert bat["근거"]  # 키워드 증거 동반
    assert 40 < bat["노출%"] < 60 and bat["등급근거"] == "graded"

    # 삼성SDI pure-play → 노출% None(100% 등치 금지).
    sdi = next(t for t in themeTool(stockCode="006400").data["themes"] if t["themeId"] == "secondaryBattery")
    assert sdi["노출%"] is None and sdi["등급근거"] == "pure_play_candidate"

    # 미존재 코드 → graceful 에러(raise 아님, ToolResult ok=False).
    bogus = themeTool(stockCode="000000")
    assert not bogus.ok and bogus.error == "company_not_found"


@pytest.mark.requires_data
def test_theme_tool_list_and_members():
    """인자 없음 → 테마 목록; themeId → 멤버."""
    assert len(themeTool().data["themes"]) == 3
    members = themeTool(themeId="secondaryBattery")
    assert members.ok and members.data["count"] > 50
