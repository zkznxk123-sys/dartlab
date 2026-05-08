"""readSkill 통합 round-trip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest


@pytest.mark.unit
def test_readskill_returns_skill_refs_with_frontmatter() -> None:
    from dartlab.ai.tools.readSkill import readSkill

    result = readSkill("회사", limit=3)
    assert isinstance(result.refs, list)
    if result.refs:
        first = result.refs[0]
        assert first.kind == "skillRef"
        assert "title" in first.payload
        assert "purpose" in first.payload
        assert "capabilityRefs" in first.payload


@pytest.mark.unit
def test_readskill_data_rows_include_when_to_use_and_required_evidence() -> None:
    from dartlab.ai.tools.readSkill import readSkill

    result = readSkill("재무제표", limit=3)
    if result.refs:
        rows = result.data.get("skills") or []
        assert rows
        sample = rows[0]
        assert "whenToUse" in sample
        assert "requiredEvidence" in sample
        assert "bodyPreview" in sample


@pytest.mark.unit
def test_readcapability_returns_api_refs() -> None:
    from dartlab.ai.tools.readCapability import readCapability

    result = readCapability("scan growth", limit=5)
    assert result.ok is True
    assert any(ref.kind == "apiRef" for ref in result.refs)


@dataclass
class _Provider:
    config: Any
    _idx: int = 0

    def check_available(self) -> bool:
        return True

    def generate(self, messages, tools):
        from dartlab.ai.providers import ProviderTurn, ToolCall

        self._idx += 1
        if self._idx == 1:
            return ProviderTurn(
                content="",
                tool_calls=[ToolCall(id="t1", name="read_skill", args={"query": "회사"})],
            )
        return ProviderTurn(content="BRIEF 완료", tool_calls=[])


@pytest.mark.unit
def test_brief_pass_populates_required_evidence() -> None:
    from dartlab.ai.providers import ProviderConfig
    from dartlab.ai.workbench.brief import runBrief
    from dartlab.ai.workbench.state import WorkbenchState

    state = WorkbenchState(question="회사 재무 분석")
    list(runBrief(state, _Provider(config=ProviderConfig(provider="openai", api_key="sk-test"))))
    assert any(c.get("tool") == "ReadSkill" for c in state.toolCalls)
