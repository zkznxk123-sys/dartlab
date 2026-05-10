"""5 패스 작업대 e2e — mock WorkbenchProvider 로 단순 시나리오."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from dartlab.ai.providers import ProviderConfig, ProviderTurn
from dartlab.ai.workbench.loop import WorkbenchLoop


@dataclass
class _MockProvider:
    """지정한 ProviderTurn 시퀀스를 round-robin 으로 반환."""

    config: ProviderConfig = field(default_factory=lambda: ProviderConfig(provider="openai", apiKey="sk-test"))
    script: list[ProviderTurn] = field(default_factory=list)
    _idx: int = 0

    def checkAvailable(self) -> bool:
        return True

    def generate(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> ProviderTurn:
        if self._idx < len(self.script):
            turn = self.script[self._idx]
            self._idx += 1
            return turn
        return ProviderTurn(content="(no more script)", toolCalls=[])


def _text(content: str) -> ProviderTurn:
    return ProviderTurn(content=content, toolCalls=[])


@pytest.mark.unit
def test_workbench_dispatches_to_llm_path_when_provider_real() -> None:
    provider = _MockProvider(
        script=[
            _text("BRIEF 결과"),
            _text("WORK 결과"),
            _text("CRITIQUE 결과"),
            _text("COMPOSE 답안"),
            _text("HARVEST 결과"),
        ]
    )
    loop = WorkbenchLoop()
    events = list(loop.stream("hi", provider=provider))
    kinds = {e.kind for e in events}
    assert "pass_enter" in kinds
    assert "pass_exit" in kinds
    assert "answer" in kinds
    assert "done" in kinds


@pytest.mark.unit
def test_workbench_5_passes_invoked_in_order() -> None:
    provider = _MockProvider(script=[_text("ok")] * 6)
    loop = WorkbenchLoop()
    pass_order: list[str] = []
    for ev in loop.stream("test", provider=provider):
        if ev.kind == "pass_enter":
            pass_order.append(ev.data.get("pass", ""))
    assert pass_order[:5] == ["brief", "work", "critique", "compose", "gate"]
    assert "harvest" in pass_order


@pytest.mark.unit
def test_workbench_legacy_path_when_provider_dartlab() -> None:
    """provider 미지정 시 기존 휴리스틱 path."""
    loop = WorkbenchLoop()
    events = list(loop.stream("삼성전자 005930"))
    kinds = [e.kind for e in events]
    assert any(k == "graph_node" for k in kinds)
    assert any(k in {"answer", "chunk", "unable"} for k in kinds)


@pytest.mark.unit
def test_done_event_carries_evidence_and_normalized_status() -> None:
    """done event 가 evidence/claims/artifacts 를 실어 보내고, responseStatus 가 정규화 ('done' → 'ok')."""
    provider = _MockProvider(
        script=[_text("brief"), _text("work"), _text("critique"), _text("answer text"), _text("harvest")]
    )
    loop = WorkbenchLoop()
    events = list(loop.stream("hi", provider=provider))
    done = next((e for e in events if e.kind == "done"), None)
    assert done is not None
    # evidence/claims/artifacts 키가 존재하고 list 형
    assert isinstance(done.data.get("evidence"), list)
    assert isinstance(done.data.get("claims"), list)
    assert isinstance(done.data.get("artifacts"), list)
    # responseStatus 정규화
    meta = done.data.get("responseMeta") or {}
    assert meta.get("responseStatus") in {"ok", "failed"}
    # 정상 시 failureReason 없음
    if meta.get("responseStatus") == "ok":
        assert "failureReason" not in meta


@pytest.mark.unit
def test_inject_step_dependency_inherits_target_from_scan() -> None:
    """scan step 결과 ref 의 stockCode 를 다음 Company step 의 target 으로 inject."""
    from dataclasses import dataclass
    from dataclasses import field as _field

    from dartlab.ai.contracts import Ref
    from dartlab.ai.workbench.loop import _injectStepDependency

    @dataclass
    class _MockResult:
        refs: list[Ref] = _field(default_factory=list)

    scan_result = _MockResult(
        refs=[
            Ref(
                id="table:scan:growth",
                kind="tableRef",
                title="growth scan",
                source="scan",
                payload={
                    "axis": "growth",
                    "rows": [
                        {"stockCode": "005930", "name": "삼성전자"},
                        {"stockCode": "005380", "name": "현대차"},
                    ],
                },
            )
        ]
    )
    prevResults = [{"plan": {"args": {"plan": {"apiRef": "scan.growth"}}}, "result": scan_result}]
    plan = {
        "tool": "engine_call",
        "args": {"plan": {"apiRef": "Company.show", "_inheritTargetsFrom": 0}},
    }
    injected = _injectStepDependency(plan, prevResults)
    assert injected["args"]["plan"].get("target") == "005930"


@pytest.mark.unit
def test_inject_step_dependency_passthrough_when_no_meta() -> None:
    """_inheritTargetsFrom 메타가 없으면 plan 그대로 반환 (회귀 보호)."""
    from dartlab.ai.workbench.loop import _injectStepDependency

    plan = {"tool": "engine_call", "args": {"plan": {"apiRef": "Company.show", "target": "005930"}}}
    injected = _injectStepDependency(plan, [])
    assert injected == plan
