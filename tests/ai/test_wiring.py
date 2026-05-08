"""5 가지 wiring 회귀 가드 — recall+lens / compiler trigger / frontmatter / CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


@pytest.mark.unit
def test_brief_lens_selection_simple_question_returns_no_lens() -> None:
    from dartlab.ai.workbench.brief import _selectLenses

    assert _selectLenses("hi") == []
    assert _selectLenses("삼성전자 종가") == []


@pytest.mark.unit
def test_brief_lens_selection_complex_question_activates_panel() -> None:
    from dartlab.ai.workbench.brief import _selectLenses

    lenses = _selectLenses("삼성전자 vs SK하이닉스 영업이익 비교")
    assert lenses

    lenses2 = _selectLenses("거시 금리 환경에서 재무제표 마진 분석")
    assert "fundamental" in lenses2
    assert "macro" in lenses2


@pytest.mark.unit
def test_brief_context_builder_includes_recall_and_lens(monkeypatch, tmp_path) -> None:
    from dartlab.ai.memory import decisions
    from dartlab.ai.workbench.brief import _buildBriefContext
    from dartlab.ai.workbench.state import WorkbenchState

    monkeypatch.setattr(decisions, "_DECISIONS_PATH", tmp_path / "decisions.jsonl")
    decisions.remember("이전 분석에서 PER 12 가 적정")

    state = WorkbenchState(question="삼성전자 PER 분석")
    state.recall = decisions.recall("삼성전자 PER", k=3)
    ctx = _buildBriefContext(state, lenses=["fundamental"])
    assert "최근 기억" in ctx
    assert "활성 lens" in ctx
    assert "fundamental" in ctx


@pytest.mark.unit
def test_frontmatter_update_status_round_trip(tmp_path) -> None:
    from dartlab.ai.memory.frontmatter import readStatus, updateStatus

    spec = tmp_path / "test.md"
    spec.write_text(
        "---\nid: engines.test.x\nstatus: unverified\nkind: generated\n---\n본문\n",
        encoding="utf-8",
    )
    assert readStatus(spec) == "unverified"
    assert updateStatus(spec, "observed") is True
    assert readStatus(spec) == "observed"
    text = spec.read_text(encoding="utf-8")
    assert "본문" in text
    assert "id: engines.test.x" in text


@pytest.mark.unit
def test_frontmatter_rejects_invalid_status(tmp_path) -> None:
    from dartlab.ai.memory.frontmatter import updateStatus

    spec = tmp_path / "x.md"
    spec.write_text("---\nstatus: unverified\n---\n", encoding="utf-8")
    with pytest.raises(ValueError):
        updateStatus(spec, "garbage")


@pytest.mark.unit
def test_deprecated_tools_removed_from_registry() -> None:
    """P-revised: skill_search / generated_spec_search / engine_call / verify_answer / read / write 가 registry 에서 제거됨."""
    from dartlab.ai.tools.registry import _SPECS

    deprecated = {"skill_search", "generated_spec_search", "engine_call", "verify_answer", "read", "write"}
    assert deprecated.isdisjoint(set(_SPECS.keys()))


@dataclass
class _MockProvider:
    config: Any
    script_idx: int = 0
    script: list = field(default_factory=list)

    def check_available(self) -> bool:
        return True

    def generate(self, messages, tools):
        from dartlab.ai.providers import ProviderTurn

        if self.script_idx < len(self.script):
            turn = self.script[self.script_idx]
            self.script_idx += 1
            return turn
        return ProviderTurn(content="", tool_calls=[])


@pytest.mark.unit
def test_brief_pass_invokes_read_skill() -> None:
    from dartlab.ai.providers import ProviderConfig, ProviderTurn, ToolCall
    from dartlab.ai.workbench.brief import runBrief
    from dartlab.ai.workbench.state import WorkbenchState

    provider = _MockProvider(
        config=ProviderConfig(provider="openai", api_key="sk-test"),
        script=[
            ProviderTurn(
                content="",
                tool_calls=[ToolCall(id="t1", name="read_skill", args={"query": "회사"})],
            ),
            ProviderTurn(content="BRIEF 완료", tool_calls=[]),
        ],
    )
    state = WorkbenchState(question="회사 재무 분석")
    list(runBrief(state, provider))
    assert any(c.get("tool") == "ReadSkill" for c in state.toolCalls)
