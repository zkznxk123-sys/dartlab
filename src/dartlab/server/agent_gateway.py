"""AG-UI compatible Agent Gateway for DartLab."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.research_graph import DartLabResearchGraph

from .models import AgentRunRequest
from .streaming import _sync_gen_to_async

_TOOL_DISPLAY = {
    "search_reference": "search reference",
    "read_context": "read context",
    "inspect_dataset": "inspect dataset",
    "run_python": "run python",
    "engine_call": "engine call",
    "compile_visual": "compile visual",
    "verify": "verify",
}

_ALLOWED_EVENTS = {
    "TEXT_MESSAGE_START",
    "TEXT_MESSAGE_CONTENT",
    "TEXT_MESSAGE_END",
    "TOOL_CALL_START",
    "TOOL_CALL_ARGS",
    "TOOL_CALL_END",
    "TOOL_CALL_RESULT",
    "STATE_SNAPSHOT",
    "STATE_DELTA",
    "MESSAGES_SNAPSHOT",
    "ACTIVITY_SNAPSHOT",
    "ACTIVITY_DELTA",
    "RUN_FINISHED",
    "RUN_ERROR",
}


async def stream_agent_run(req: AgentRunRequest) -> AsyncIterator[dict[str, str]]:
    """Stream one DartLab research run using the public AG-UI event contract."""
    question = _last_user_message(req)
    run_id = req.threadId or "dartlab-thread"
    message_id = f"msg-{run_id}"
    graph = DartLabResearchGraph()
    text_started = False

    yield _event(
        "STATE_SNAPSHOT",
        {
            "runId": run_id,
            "agentId": req.agentId or "dartlab-research",
            "status": "running",
            "graph": {"name": "DartLabResearchGraph", "nodes": list(graph.nodes)},
        },
    )
    yield _activity("계획을 세우고 필요한 근거를 확인합니다.", status="done")

    try:
        async for internal in _sync_gen_to_async(graph.stream, question, **_kernel_kwargs(req)):
            for public in _public_events(internal, run_id=run_id, message_id=message_id):
                if public["event"] == "TEXT_MESSAGE_CONTENT" and not text_started:
                    text_started = True
                    yield _event("TEXT_MESSAGE_START", {"messageId": message_id, "role": "assistant"})
                yield public
        if text_started:
            yield _event("TEXT_MESSAGE_END", {"messageId": message_id})
    except Exception as exc:  # noqa: BLE001
        yield _event("RUN_ERROR", {"runId": run_id, "message": _public_failure(str(exc)), "code": "agent_run_failed"})


def _public_events(event: TraceEvent, *, run_id: str, message_id: str) -> list[dict[str, str]]:
    kind = event.kind
    data = event.data
    if kind == "graph_node":
        state = data.get("state") if isinstance(data.get("state"), dict) else {}
        return [
            _event(
                "STATE_DELTA",
                {
                    "runId": run_id,
                    "status": data.get("status") or "running",
                    "currentNode": data.get("node"),
                    "state": _public_graph_state(state),
                },
            ),
            _activity(str(data.get("summary") or "분석 단계를 진행합니다."), status="done"),
        ]
    if kind == "plan":
        skills = data.get("selectedSkillIds") if isinstance(data.get("selectedSkillIds"), list) else []
        target = ", ".join(str(item) for item in skills[:3])
        return [_activity(f"분석 경로를 정했습니다{': ' + target if target else ''}", refs=[])]
    if kind in {"tool_start", "tool_call"}:
        tool = _tool_name(data)
        if tool not in {"engine_call", "run_python", "compile_visual"}:
            return []
        return [
            _event(
                "TOOL_CALL_START",
                {
                    "runId": run_id,
                    "messageId": message_id,
                    "toolCallId": str(data.get("id") or tool),
                    "toolName": _display_tool(tool),
                    "status": "running",
                },
            ),
            _activity(f"{_display_tool(tool)} 실행 중", status="running"),
        ]
    if kind == "tool_result":
        tool = _tool_name(data)
        if tool not in {"engine_call", "run_python", "compile_visual"}:
            return []
        status = "error" if data.get("status") == "error" else "done"
        return [
            _event(
                "TOOL_CALL_RESULT",
                {
                    "runId": run_id,
                    "messageId": message_id,
                    "toolCallId": str(data.get("id") or tool),
                    "toolName": _display_tool(tool),
                    "status": status,
                    "summary": str(data.get("outputSummary") or data.get("summary") or ""),
                    "refs": [str(v) for v in data.get("evidenceRefs") or []],
                    "artifacts": [a for a in data.get("artifacts") or [] if isinstance(a, dict)],
                },
            ),
            _event(
                "TOOL_CALL_END",
                {
                    "runId": run_id,
                    "messageId": message_id,
                    "toolCallId": str(data.get("id") or tool),
                    "toolName": _display_tool(tool),
                    "status": status,
                },
            ),
            _activity(f"{_display_tool(tool)} 실행함", status=status),
        ]
    if kind == "reference":
        refs = data.get("refs") if isinstance(data.get("refs"), list) else []
        if refs:
            return [_activity(f"근거 {len(refs)}개를 확인했습니다.", refs=_ref_ids(refs))]
        return []
    if kind == "verify":
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        if result.get("ok") is True:
            return [_activity("근거 검증을 통과했습니다.", refs=[str(data.get("refId"))] if data.get("refId") else [])]
        return [_activity("답변 초안을 다시 검증합니다.", status="running")]
    if kind == "chunk":
        text = str(data.get("text") or "")
        return [_event("TEXT_MESSAGE_CONTENT", {"messageId": message_id, "delta": text})] if text else []
    if kind == "answer":
        refs = [str(v) for v in data.get("evidenceRefs") or []]
        return [_activity(f"근거 {len(refs)}개로 답변을 작성했습니다.", refs=refs)]
    if kind == "unable":
        message = str(data.get("message") or "") or _public_failure(str(data.get("reason") or ""))
        return [_event("RUN_ERROR", {"runId": run_id, "message": message})]
    if kind == "done":
        status = "ok" if (data.get("responseMeta") or {}).get("finalEvent") == "answer" else "failed"
        refs = _ref_ids(data.get("refs") if isinstance(data.get("refs"), list) else [])
        artifacts = [a for a in data.get("artifacts") or [] if isinstance(a, dict)]
        finished = _event(
            "RUN_FINISHED",
            {
                "runId": run_id,
                "status": status,
                "refs": refs,
                "artifacts": artifacts,
                "responseMeta": _public_response_meta(data.get("responseMeta") or {}),
            },
        )
        if status == "ok":
            return [finished]
        return [
            _event(
                "RUN_ERROR",
                {
                    "runId": run_id,
                    "message": _public_failure(str((data.get("responseMeta") or {}).get("failureReason") or "")),
                },
            ),
            finished,
        ]
    if kind == "error":
        return [_event("RUN_ERROR", {"runId": run_id, "message": _public_failure(str(data.get("error") or ""))})]
    return []


def _kernel_kwargs(req: AgentRunRequest) -> dict[str, Any]:
    context = req.workspaceContext or {}
    kwargs: dict[str, Any] = {
        "provider": req.provider,
        "role": req.role,
        "model": req.model,
    }
    company = context.get("company") if isinstance(context, dict) else None
    if isinstance(company, dict):
        hint = company.get("stockCode") or company.get("corpName") or company.get("company")
        if hint:
            kwargs["stockCode"] = hint
    return {k: v for k, v in kwargs.items() if v is not None}


def _last_user_message(req: AgentRunRequest) -> str:
    for message in reversed(req.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    return ""


def _event(event_type: str, data: dict[str, Any]) -> dict[str, str]:
    if event_type not in _ALLOWED_EVENTS:
        raise ValueError(f"unsupported AG-UI event: {event_type}")
    payload = {"type": event_type, **_publicEventData(data)}
    return {"event": event_type, "data": json.dumps(payload, ensure_ascii=False, default=str)}


def _publicEventData(value):
    if isinstance(value, dict):
        return {key: _publicEventData(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_publicEventData(item) for item in value]
    if isinstance(value, str):
        return (
            value.replace("search_reference", "search reference")
            .replace("read_context", "read context")
            .replace("generated_spec_search", "generated spec search")
            .replace("engine_call", "engine call")
            .replace("run_python", "run python")
            .replace("verify_answer", "verify answer")
        )
    return value


def _activity(summary: str, *, status: str = "done", refs: list[str] | None = None) -> dict[str, str]:
    return _event(
        "ACTIVITY_DELTA",
        {
            "status": status,
            "summary": summary,
            "refs": refs or [],
        },
    )


def _tool_name(data: dict[str, Any]) -> str:
    return str(data.get("name") or data.get("tool") or "tool")


def _display_tool(tool: str) -> str:
    return _TOOL_DISPLAY.get(tool, str(tool).replace("_", " "))


def _ref_ids(refs: list[Any]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        if isinstance(ref, dict) and ref.get("id"):
            out.append(str(ref["id"]))
        elif isinstance(ref, str):
            out.append(ref)
    return out


def _public_response_meta(meta: dict[str, Any]) -> dict[str, Any]:
    allowed = {"refCount", "verificationOk", "artifactCount", "activityCount", "responseStatus"}
    return {key: meta.get(key) for key in allowed if key in meta}


def _public_graph_state(state: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "currentNode",
        "selectedSkills",
        "evidenceRefs",
        "toolCallCount",
        "finalAnswerSeen",
        "failure",
    }
    return {key: state.get(key) for key in allowed if key in state}


def _public_failure(reason: str) -> str:
    text = reason.strip()
    if not text:
        return "최종 답변을 생성하지 못했습니다."
    labels = {
        "provider": "provider 연결 실패",
        "tool": "도구 실행 실패",
        "verification": "근거 검증 실패",
        "direct_answer": "최종 답변 생성 실패",
        "ref_only": "근거 기반 답변 생성 실패",
    }
    for needle, label in labels.items():
        if needle in text:
            return label
    return "최종 답변을 생성하지 못했습니다."
