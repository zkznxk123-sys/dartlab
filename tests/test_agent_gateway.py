from __future__ import annotations

import asyncio
import json

import pytest

from dartlab.ai.contracts import TraceEvent
from dartlab.server.models import AgentRunMessage, AgentRunRequest

pytestmark = pytest.mark.unit


def _payload(event: dict[str, str]) -> dict:
    return json.loads(event["data"])


def test_agent_gateway_public_events_hide_internal_kernel_names(monkeypatch) -> None:
    import dartlab.server.agent_gateway as agent_gateway

    class FakeGraph:
        nodes = (
            "route_intent",
            "select_skill",
            "plan_evidence",
            "execute_tool",
            "observe_result",
            "verify_claims",
            "compose_answer",
            "repair_or_fail",
        )

        def stream(self, question: str, **kwargs):
            assert question == "너 뭐 할 수 있니"
            yield TraceEvent("plan", {"selectedSkillIds": ["start.useSkillsCatalog"]})
            yield TraceEvent("reference", {"refs": [{"id": "skill:start"}], "source": "search_reference"})
            yield TraceEvent("tool_start", {"name": "search_reference", "id": "hidden-search"})
            yield TraceEvent("tool_start", {"name": "run_python", "id": "code-1"})
            yield TraceEvent("tool_result", {"name": "run_python", "id": "code-1", "outputSummary": "계산 완료"})
            yield TraceEvent("chunk", {"text": "DartLab은 재무/공시/시장 데이터를 근거로 분석합니다."})
            yield TraceEvent("answer", {"evidenceRefs": ["skill:start"]})
            yield TraceEvent(
                "done",
                {
                    "refs": [{"id": "skill:start"}],
                    "responseMeta": {"finalEvent": "answer", "refCount": 1, "verificationOk": True},
                },
            )

    monkeypatch.setattr(agent_gateway, "WorkbenchLoop", FakeGraph)
    # workspaceContext.mode="analyze" → workbench 분기 (FakeGraph) 강제. chat 분기 (runAgent) 우회.
    req = AgentRunRequest(
        messages=[AgentRunMessage(role="user", content="너 뭐 할 수 있니")],
        workspaceContext={"mode": "analyze"},
    )

    async def collect():
        return [event async for event in agent_gateway.stream_agent_run(req)]

    events = asyncio.run(collect())
    public_text = "\n".join(event["event"] + " " + event["data"] for event in events)

    assert "search_reference" not in public_text
    assert "hidden-search" not in public_text
    assert "prose_without_finalize" not in public_text
    assert "draft_rejected" not in public_text
    assert "TEXT_MESSAGE_CONTENT" in {event["event"] for event in events}
    assert "TOOL_CALL_START" in {event["event"] for event in events}
    assert "RUN_FINISHED" in {event["event"] for event in events}
    assert any(_payload(event).get("toolName") == "RunPython" for event in events)


def test_agent_gateway_failure_reason_is_public(monkeypatch) -> None:
    import dartlab.server.agent_gateway as agent_gateway

    class FakeGraph:
        nodes = ("route_intent", "repair_or_fail")

        def stream(self, question: str, **kwargs):
            yield TraceEvent("unable", {"reason": "prose_without_finalize"})

    monkeypatch.setattr(agent_gateway, "WorkbenchLoop", FakeGraph)
    req = AgentRunRequest(
        messages=[AgentRunMessage(role="user", content="질문")],
        workspaceContext={"mode": "analyze"},
    )

    async def collect():
        return [event async for event in agent_gateway.stream_agent_run(req)]

    events = asyncio.run(collect())
    errors = [_payload(event) for event in events if event["event"] == "RUN_ERROR"]

    assert errors
    assert errors[0]["message"] == "최종 답변을 생성하지 못했습니다."
    assert "prose_without_finalize" not in json.dumps(errors, ensure_ascii=False)


def test_agent_gateway_failed_done_emits_public_error_without_internal_meta(monkeypatch) -> None:
    import dartlab.server.agent_gateway as agent_gateway

    class FakeGraph:
        nodes = ("route_intent", "repair_or_fail")

        def stream(self, question: str, **kwargs):
            yield TraceEvent(
                "done",
                {
                    "refs": [],
                    "responseMeta": {
                        "finalEvent": "prose_without_finalize",
                        "failureReason": "prose_without_finalize",
                        "refCount": 0,
                    },
                },
            )

    monkeypatch.setattr(agent_gateway, "WorkbenchLoop", FakeGraph)
    req = AgentRunRequest(
        messages=[AgentRunMessage(role="user", content="질문")],
        workspaceContext={"mode": "analyze"},
    )

    async def collect():
        return [event async for event in agent_gateway.stream_agent_run(req)]

    events = asyncio.run(collect())
    public_text = json.dumps([_payload(event) for event in events], ensure_ascii=False)

    assert any(event["event"] == "RUN_ERROR" for event in events)
    assert any(_payload(event).get("status") == "failed" for event in events if event["event"] == "RUN_FINISHED")
    assert "prose_without_finalize" not in public_text


def test_agent_runs_endpoint_streams_only_public_events(monkeypatch) -> None:
    from starlette.testclient import TestClient

    import dartlab.server.api.agent as agent_api
    from dartlab.server import app

    async def fake_stream(req):
        yield {"event": "ACTIVITY_DELTA", "data": json.dumps({"summary": "근거 확인", "status": "done"})}
        yield {"event": "RUN_FINISHED", "data": json.dumps({"status": "ok", "refs": ["skill:start"]})}

    monkeypatch.setattr(agent_api, "stream_agent_run", fake_stream)
    with TestClient(app, raise_server_exceptions=False) as client:
        with client.stream(
            "POST",
            "/api/agent/runs",
            json={"messages": [{"role": "user", "content": "너 뭐 할 수 있니"}], "stream": True},
        ) as response:
            body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: ACTIVITY_DELTA" in body
    assert "event: RUN_FINISHED" in body
    assert "search_reference" not in body


def test_api_ask_stream_uses_public_agent_events() -> None:
    from dartlab.server.api.ask import _streamPublicAsk
    from dartlab.server.models import AskRequest

    async def collect():
        return [event async for event in _streamPublicAsk(AskRequest(question="너 뭐 할 수 있니", stream=True))]

    events = asyncio.run(collect())
    body = "\n".join(event["event"] for event in events)

    assert "TEXT_MESSAGE_CONTENT" in body
    assert "RUN_FINISHED" in body
    assert "graph_node" not in body
    assert "tool_start" not in body


def test_research_graph_emits_ordered_node_state(monkeypatch) -> None:
    from dartlab.ai.workbench import WorkbenchLoop

    events = list(WorkbenchLoop().stream("너 뭐 할 수 있니"))
    nodes = [event.data["node"] for event in events if event.kind == "graph_node"]

    # 5 패스 SSOT — workbench loop 의 GRAPH_NODES 와 일치.
    # 휴리스틱 path 는 brief→work→compose→gate 순으로 발행 (HARVEST 는 LLM 전용 no-op).
    # GATE 는 결과 + 실패 분기에서 두 번 발행될 수 있다.
    assert nodes[:4] == ["brief", "work", "compose", "gate"]
    assert events[-1].kind == "done"
