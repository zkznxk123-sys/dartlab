"""AG-UI compatible Agent Gateway for DartLab."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from dartlab.ai.agent import runAgent
from dartlab.ai.contracts import TraceEvent
from dartlab.ai.workbench import WorkbenchLoop
from dartlab.ai.workbench.intent import isAnalysisIntent

from . import agent_metrics
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
    "read_skill": "read skill",
    "read_capability": "read capability",
    "web_search": "web search",
    "save_artifact": "save artifact",
}

# UI 가 ToolBlock 카드로 표현할 도구 화이트리스트.
# agent.py 가 자율 호출하는 6 개 + workbench 5 패스의 3 개.
_PUBLIC_TOOL_NAMES = {
    "run_python",
    "engine_call",
    "compile_visual",
    "read_skill",
    "read_capability",
    "web_search",
    "save_artifact",
    "inspect_dataset",
    "verify",
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
    "VIEW_SPEC",
    "RUN_FINISHED",
    "RUN_ERROR",
}


async def stream_agent_run(req: AgentRunRequest) -> AsyncIterator[dict[str, str]]:
    """Stream one DartLab run using the public AG-UI event contract.

    분기:
    - 명시적 mode="analyze" / "research" / 종목 컨텍스트 / 분석 키워드 → WorkbenchLoop (5 패스)
    - 그 외 (메타 / chitchat / 일반 대화) → runAgent (LLM 자율 + tool calling)

    회귀 방지: memory/feedback_no_graph_regression.md — runAgent 가 본체. WorkbenchLoop 는 옵션.
    """
    question = _last_user_message(req)
    run_id = req.threadId or "dartlab-thread"
    message_id = f"msg-{run_id}"
    text_started = False

    kernel_kwargs = _kernel_kwargs(req)
    use_workbench = _shouldUseWorkbench(req, question, kernel_kwargs)

    if use_workbench:
        graph = WorkbenchLoop()
        agent_metrics.record("workbench")
        yield _event(
            "STATE_SNAPSHOT",
            {
                "runId": run_id,
                "agentId": req.agentId or "dartlab-research",
                "status": "running",
                "graph": {"name": "DartLabWorkbench", "nodes": list(graph.nodes)},
                "mode": "workbench",
            },
        )
        yield _activity("계획을 세우고 필요한 근거를 확인합니다.", status="done")
        producer = lambda: graph.stream(question, **kernel_kwargs)  # noqa: E731
    else:
        provider_obj = _resolveProvider(kernel_kwargs)
        if provider_obj is None or not _isLLMProvider(provider_obj):
            # provider 미해결 — workbench 휴리스틱 fallback
            graph = WorkbenchLoop()
            agent_metrics.record("workbench-heuristic")
            yield _event(
                "STATE_SNAPSHOT",
                {
                    "runId": run_id,
                    "agentId": req.agentId or "dartlab-research",
                    "status": "running",
                    "graph": {"name": "DartLabWorkbench", "nodes": list(graph.nodes)},
                    "mode": "workbench-heuristic",
                },
            )
            producer = lambda: graph.stream(question, **kernel_kwargs)  # noqa: E731
        else:
            agent_metrics.record("agent")
            yield _event(
                "STATE_SNAPSHOT",
                {
                    "runId": run_id,
                    "agentId": req.agentId or "dartlab-agent",
                    "status": "running",
                    "graph": {"name": "DartLabAgent", "nodes": ["agent"]},
                    "mode": "agent",
                },
            )
            agent_kwargs = {**kernel_kwargs, "provider": provider_obj}
            producer = lambda: runAgent(question, **agent_kwargs)  # noqa: E731

    try:
        async for internal in _sync_gen_to_async(producer):
            for public in _public_events(internal, run_id=run_id, message_id=message_id):
                if public["event"] == "TEXT_MESSAGE_CONTENT" and not text_started:
                    text_started = True
                    yield _event("TEXT_MESSAGE_START", {"messageId": message_id, "role": "assistant"})
                yield public
        if text_started:
            yield _event("TEXT_MESSAGE_END", {"messageId": message_id})
    except Exception as exc:  # noqa: BLE001
        yield _event("RUN_ERROR", {"runId": run_id, "message": _public_failure(str(exc)), "code": "agent_run_failed"})


def _shouldUseWorkbench(req: AgentRunRequest, question: str, kernel_kwargs: dict[str, Any]) -> bool:
    """명시적 분석 모드 / 종목 컨텍스트 / 분석 키워드 → workbench. 그 외 → agent."""
    mode = ""
    context = req.workspaceContext if isinstance(req.workspaceContext, dict) else {}
    if isinstance(context, dict):
        mode = str(context.get("mode") or context.get("dialogueMode") or "").lower()
    if mode in {"analyze", "analysis", "research", "workbench"}:
        return True
    if isAnalysisIntent(question, kernel_kwargs):
        return True
    return False


def _resolveProvider(kernel_kwargs: dict[str, Any]) -> Any:
    try:
        from dartlab.ai.providers import create_provider

        return create_provider(
            provider=kernel_kwargs.get("provider"),
            model=kernel_kwargs.get("model"),
        )
    except Exception:  # noqa: BLE001
        return None


def _isLLMProvider(obj: Any) -> bool:
    """provider 가 LLM 어댑터인지 — workbench/loop 의 _isLLMProvider 와 동일 룰."""
    if obj is None or not callable(getattr(obj, "generate", None)):
        return False
    config = getattr(obj, "config", None)
    provider_id = (getattr(config, "provider", None) or "").lower()
    if provider_id not in {
        "oauth-codex",
        "openai",
        "gemini",
        "codex",
        "ollama",
        "custom",
        "groq",
        "cerebras",
        "mistral",
    }:
        return False
    try:
        return bool(obj.check_available())
    except Exception:  # noqa: BLE001
        return False


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
        if tool not in _PUBLIC_TOOL_NAMES:
            return []
        # ToolBlock 카드(TOOL_CALL_START)가 진행 표현 전담. activity 줄 중복 emit 금지.
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
        ]
    if kind == "view_spec":
        spec = data.get("spec")
        if not spec:
            return []
        return [
            _event(
                "VIEW_SPEC",
                {
                    "runId": run_id,
                    "messageId": message_id,
                    "id": data.get("id"),
                    "spec": spec,
                    "title": data.get("title"),
                    "source": data.get("source"),
                },
            )
        ]
    if kind == "tool_result":
        tool = _tool_name(data)
        if tool not in _PUBLIC_TOOL_NAMES:
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
        suggested_questions = _suggest_followups(data) if status == "ok" else []
        finished = _event(
            "RUN_FINISHED",
            {
                "runId": run_id,
                "status": status,
                "refs": refs,
                "artifacts": artifacts,
                "responseMeta": _public_response_meta(data.get("responseMeta") or {}),
                "suggestedQuestions": suggested_questions,
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
    # history: 마지막 user message (= 현재 question) 제외, 이전 대화만.
    messages = list(req.messages or [])
    history: list[dict[str, Any]] = []
    last_user_index = -1
    for idx, msg in enumerate(messages):
        if msg.role == "user" and msg.content.strip():
            last_user_index = idx
    for idx, msg in enumerate(messages):
        if idx == last_user_index:
            continue
        if msg.role in {"user", "assistant"} and msg.content:
            history.append({"role": msg.role, "content": msg.content})
    if history:
        kwargs["history"] = history
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


def _suggest_followups(done_data: dict[str, Any]) -> list[str]:
    """답변 종료 시점 휴리스틱 follow-up 추천 질문 3 개.

    Perplexity 식 — 사용자가 추가 탐색을 쉽게 할 수 있게. backend 컨텍스트
    (responseMeta.stockCode, refs, evidenceRefs) 기반. LLM 추가 호출 없이 가벼움.
    """
    meta = done_data.get("responseMeta") if isinstance(done_data.get("responseMeta"), dict) else {}
    stock = meta.get("stockCode") or meta.get("company") or ""
    if stock:
        return [
            f"{stock}의 수익성·안정성·성장성 축으로 비교해줘",
            f"{stock}의 최근 공시에서 의미 있는 변화는?",
            "같은 산업의 다른 회사와 비교해줘",
        ]
    topic = meta.get("topic") or ""
    if topic:
        return [
            f"{topic} 관련 주요 종목 후보를 추려줘",
            f"{topic} 의 최근 추세는 어떤가?",
            f"{topic} 와 가장 연관 있는 매크로 지표는?",
        ]
    return [
        "관련된 매크로 흐름을 보여줘",
        "비슷한 사례를 더 보여줘",
        "이 결과를 표·차트로 정리해줘",
    ]


def _activity(summary: str, *, status: str = "done", refs: list[str] | None = None) -> dict[str, str]:
    return _event(
        "ACTIVITY_DELTA",
        {
            "status": status,
            "summary": summary,
            "refs": refs or [],
        },
    )


def _view_spec(
    spec: dict[str, Any],
    *,
    run_id: str,
    message_id: str,
    source: str | None = None,
    title: str | None = None,
) -> dict[str, str]:
    """View-spec part — 차트/표/대시보드 같은 시각 답변을 메시지 흐름에 인라인.

    spec 형식: viewSpec.normalizeViewSpec 가 받는 모양 (widgets[]/charts[]/component).
    분석 워크벤치 정체성의 주체. tool/activity 보다 시각적 위계가 높다.
    """
    payload: dict[str, Any] = {
        "runId": run_id,
        "messageId": message_id,
        "spec": spec,
    }
    if source:
        payload["source"] = source
    if title:
        payload["title"] = title
    return _event("VIEW_SPEC", payload)


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
