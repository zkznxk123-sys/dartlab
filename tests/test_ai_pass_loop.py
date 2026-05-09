"""PassLoop — 5 패스 작업대 end-to-end (mock provider).

API 키 없이 LLM-driven 흐름이 BRIEF→WORK→CRITIQUE→COMPOSE→GATE→HARVEST 를
지나며 도구를 호출하고 답을 만드는지 본다.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.providers.base import LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec
from dartlab.ai.workbench import PassLoop
from dartlab.ai.workbench.passLoop import PASS_NODES


@pytest.fixture(autouse=True)
def _isolate_memory(tmp_path, monkeypatch):
    """passLoop 가 호출하는 remember/recordSkillUsage 가 사용자 홈을 오염시키지 않게."""

    monkeypatch.setenv("DARTLAB_DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    monkeypatch.setenv("DARTLAB_SKILL_STATS_PATH", str(tmp_path / "skill_stats.json"))


class _ScriptedProvider:
    """Provider that replays pre-programmed event scripts per call."""

    name = "mock"
    resolved_model = "mock-model"

    def __init__(self, scripts: list[list[LLMEvent]]):
        self._scripts = list(scripts)
        self._index = 0

    def check_available(self) -> bool:
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
        return {"name": spec.name, "description": spec.description, "input_schema": spec.inputSchema}

    def complete(
        self,
        messages: list[Msg],
        tools: list[ToolSpec],
        *,
        stream: bool = True,
    ) -> Iterator[LLMEvent]:
        if self._index >= len(self._scripts):
            yield LLMEvent("text", {"delta": ""})
            yield LLMEvent("stop", {"reason": "exhausted"})
            return
        script = self._scripts[self._index]
        self._index += 1
        for ev in script:
            yield ev


def _stop(reason: str = "end_turn") -> LLMEvent:
    return LLMEvent("stop", {"reason": reason})


def test_pass_loop_executes_full_pipeline_with_mock_provider():
    scripts: list[list[LLMEvent]] = [
        # BRIEF — 도구 없이 한 단락 요약 (skip read_skill 호출하지 않게)
        [
            LLMEvent("text", {"delta": "삼성전자 수익성 분석 계획: BS/IS/CF 3 개년 + ROE/OPM/부채비율."}),
            _stop(),
        ],
        # WORK — 한 줄 요약, 도구는 생략 (mock 환경)
        [
            LLMEvent("text", {"delta": "ROE 12.3% (valueRef:roe), OPM 18.5% (valueRef:opm)."}),
            _stop(),
        ],
        # CRITIQUE
        [
            LLMEvent("text", {"delta": "유지. 반대 가설 점검 완료."}),
            _stop(),
        ],
        # COMPOSE — 답안 (숫자 포함, ref 형식 인용)
        [
            LLMEvent(
                "text",
                {"delta": "삼성전자 수익성: ROE 12.3% [valueRef:roe], OPM 18.5% [valueRef:opm]."},
            ),
            _stop(),
        ],
    ]

    provider = _ScriptedProvider(scripts)
    loop = PassLoop(provider=provider)

    events = list(loop.stream("삼성전자 수익성 분석"))
    kinds = [event.kind for event in events]

    assert "brief_done" in kinds
    assert "work_done" in kinds
    assert "critique_done" in kinds
    assert "answer" in kinds
    assert "verify" in kinds
    assert "harvest" in kinds
    assert kinds[-1] == "done"


def test_pass_loop_node_order_matches_ssot():
    assert PASS_NODES == ("brief", "work", "critique", "compose", "gate", "harvest")


def test_pass_loop_marks_failure_when_answer_lacks_value_refs():
    # 답에 숫자만 있고 valueRef 없음 → GATE 가 실패 마킹
    scripts: list[list[LLMEvent]] = [
        [LLMEvent("text", {"delta": "BRIEF"}), _stop()],
        [LLMEvent("text", {"delta": "WORK summary"}), _stop()],
        [LLMEvent("text", {"delta": "유지"}), _stop()],
        [LLMEvent("text", {"delta": "삼성전자 ROE 는 12.3%."}), _stop()],
    ]
    loop = PassLoop(provider=_ScriptedProvider(scripts))
    events = list(loop.stream("삼성전자 수익성"))
    final = events[-1]

    assert final.kind == "done"
    assert final.data["responseMeta"]["responseStatus"] == "failed"
    assert "numeric_claim_without_value_ref" in final.data["responseMeta"]["failureReason"]


def test_pass_loop_passes_text_only_answers_without_numbers_through_gate():
    scripts: list[list[LLMEvent]] = [
        [LLMEvent("text", {"delta": "BRIEF"}), _stop()],
        [LLMEvent("text", {"delta": "WORK"}), _stop()],
        [LLMEvent("text", {"delta": "유지"}), _stop()],
        [LLMEvent("text", {"delta": "이 질문은 정량 데이터가 필요하지 않다."}), _stop()],
    ]
    loop = PassLoop(provider=_ScriptedProvider(scripts))
    events = list(loop.stream("DartLab 의 사상은 무엇인가"))
    final = events[-1]

    assert final.kind == "done"
    assert final.data["responseMeta"]["responseStatus"] == "ok"


def test_kernel_routes_explicit_provider_to_pass_loop(monkeypatch: pytest.MonkeyPatch):
    """provider != 'dartlab' 일 때 kernel.py 가 PassLoop 로 라우팅."""

    from dartlab.ai import kernel

    captured: dict[str, Any] = {}

    class _CapturingPassLoop:
        def __init__(self, *, providerConfig=None, **_kwargs):
            captured["config"] = providerConfig

        def stream(self, question, **_):
            captured["question"] = question
            from dartlab.ai.contracts import TraceEvent

            yield TraceEvent("done", {"responseMeta": {"finalEvent": "answer", "responseStatus": "ok"}})

    monkeypatch.setattr("dartlab.ai.workbench.PassLoop", _CapturingPassLoop)

    events = list(kernel._ask_events("질문", provider="anthropic", model="claude-x"))

    assert captured.get("question") == "질문"
    assert captured["config"].provider == "anthropic"
    assert captured["config"].model == "claude-x"
    assert events[-1].kind == "done"


def test_kernel_default_uses_legacy_workbench_loop(monkeypatch: pytest.MonkeyPatch):
    """provider 가 dartlab 또는 미지정이면 기존 휴리스틱 loop 그대로."""

    from dartlab.ai import kernel

    used = {"legacy": False}

    class _Sentinel:
        nodes: tuple[str, ...] = ()

        def stream(self, question, **_):
            used["legacy"] = True
            from dartlab.ai.contracts import TraceEvent

            yield TraceEvent("graph_node", {"node": "routeIntent", "summary": "", "status": "running"})
            yield TraceEvent("done", {"responseMeta": {"finalEvent": "answer", "responseStatus": "ok"}})

    monkeypatch.setattr("dartlab.ai.kernel.DartLabResearchGraph", _Sentinel)

    list(kernel._ask_events("질문", provider="dartlab"))
    assert used["legacy"] is True
