"""HARVEST + propose_skill 자기진화."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from dartlab.ai.providers import ProviderConfig, ProviderTurn, ToolCall
from dartlab.ai.workbench.harvest import runHarvest
from dartlab.ai.workbench.state import WorkbenchState


@dataclass
class _Provider:
    config: ProviderConfig = field(default_factory=lambda: ProviderConfig(provider="openai", api_key="sk-test"))
    plan: list[dict] | None = None

    def check_available(self) -> bool:
        return True

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self.plan:
            args = self.plan[0]
            return ProviderTurn(
                content="",
                tool_calls=[ToolCall(id="t1", name="propose_skill", args=args)],
            )
        return ProviderTurn(content="신규 후보 없음", tool_calls=[])


@pytest.mark.unit
def test_harvest_records_proposal_when_propose_skill_called(monkeypatch, tmp_path) -> None:
    from dartlab.ai.tools import proposeSkill as module

    monkeypatch.setattr(module, "_SPEC_ROOT", tmp_path / "specs")

    state = WorkbenchState(question="새 패턴 트리거")
    provider = _Provider(
        plan=[
            {
                "skillId": "engines.scan.harvested",
                "title": "수확된 패턴",
                "purpose": "반복 사용된 capability 조합",
                "category": "engines",
                "capabilityRefs": ["scan.profitability"],
                "requiredEvidence": ["target", "metric"],
                "body": "본문",
            }
        ]
    )
    list(runHarvest(state, provider))
    assert any(c.get("tool") == "propose_skill" and c.get("ok") for c in state.toolCalls)
    assert state.harvestProposals
    target = tmp_path / "specs" / "engines" / "scan" / "harvested.md"
    assert target.exists()


@pytest.mark.unit
def test_harvest_no_proposal_when_no_pattern() -> None:
    state = WorkbenchState(question="단순 질문")
    provider = _Provider(plan=None)
    list(runHarvest(state, provider))
    assert not state.harvestProposals
