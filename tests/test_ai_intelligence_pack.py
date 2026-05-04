"""인텔리전스 팩은 레거시 runtime 대신 Skill/capability 검색으로 흡수된다."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_generated_spec_search_replaces_runtime_intelligence_pack():
    from dartlab.ai.tools.generatedSpecSearch import generatedSpecSearch

    result = generatedSpecSearch("재무상태표 Company show")

    assert result.ok is True
    assert any(ref.payload.get("apiRef") == "Company.show" for ref in result.refs)


def test_skill_search_replaces_runtime_pack_summary():
    from dartlab.ai.tools.skillSearch import skillSearch

    result = skillSearch("처음 온 외부 AI 시작점")

    assert result.ok is True
    assert any(ref.id == "skill:start.dartlabSkillOs" for ref in result.refs)
