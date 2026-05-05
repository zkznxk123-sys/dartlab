"""5 패스 공용 LLM-도구 루프 (옛 WorkbenchProvider / generate() 시스템).

provider.generate(messages, tools) -> ProviderTurn 호출 + tool_calls 실행 + tool_result 메시지 이어붙여 다음 라운드.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import Ref, TraceEvent
from dartlab.ai.providers import ProviderTurn, WorkbenchProvider
from dartlab.ai.tools.registry import _SPECS as TOOL_SPECS
from dartlab.ai.tools.registry import executeTool

from .state import WorkbenchState


def runLLMPass(
    state: WorkbenchState,
    provider: WorkbenchProvider,
    *,
    passName: str,
    systemPrompt: str,
    userContext: str,
    allowedTools: list[str],
    maxRounds: int = 6,
) -> Iterator[TraceEvent]:
    state.currentPass = passName
    yield TraceEvent(kind="pass_enter", data={"pass": passName})

    tool_specs_objs = [TOOL_SPECS[name] for name in allowedTools if name in TOOL_SPECS]
    tools_payload = [_toolToOpenAIFormat(spec) for spec in tool_specs_objs]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": systemPrompt},
        {"role": "user", "content": userContext},
    ]

    rounds_used = 0
    for round_idx in range(maxRounds):
        rounds_used = round_idx + 1
        try:
            turn: ProviderTurn = provider.generate(messages, tools_payload)
        except Exception as exc:  # noqa: BLE001
            yield TraceEvent(
                kind="llm_error",
                data={"pass": passName, "round": round_idx, "error": str(exc), "type": type(exc).__name__},
            )
            break

        if turn.content:
            yield TraceEvent(
                kind="llm_text",
                data={"pass": passName, "round": round_idx, "text": turn.content},
            )

        for call in turn.tool_calls:
            yield TraceEvent(
                kind="llm_tool_use",
                data={
                    "pass": passName,
                    "round": round_idx,
                    "id": call.id,
                    "name": call.name,
                    "input": call.args,
                },
            )

        # assistant 메시지 추가 (tool_calls 포함)
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": turn.content or ""}
        if turn.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": json.dumps(c.args, ensure_ascii=False)},
                }
                for c in turn.tool_calls
            ]
        messages.append(assistant_msg)

        if not turn.tool_calls:
            yield TraceEvent(kind="llm_stop", data={"pass": passName, "round": round_idx, "reason": "no_tool_calls"})
            break

        for call in turn.tool_calls:
            tool_start = time.monotonic()
            result = executeTool(call.name, call.args or {})
            tool_duration_ms = int((time.monotonic() - tool_start) * 1000)

            state.toolCalls.append(
                {
                    "pass": passName,
                    "tool": call.name,
                    "args": call.args,
                    "ok": result.get("ok"),
                    "durationMs": tool_duration_ms,
                }
            )
            for ref_dict in result.get("refs") or []:
                state.refs.append(_refFromDict(ref_dict))

            yield TraceEvent(
                kind="tool_result",
                data={
                    "pass": passName,
                    "tool": call.name,
                    "ok": result.get("ok"),
                    "summary": result.get("summary"),
                    "refs": [r.get("id") for r in result.get("refs") or []],
                    "error": result.get("error"),
                },
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    yield TraceEvent(kind="pass_exit", data={"pass": passName, "rounds": rounds_used})


def _toolToOpenAIFormat(spec: Any) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.inputSchema,
        },
    }


def _refFromDict(d: dict[str, Any]) -> Ref:
    return Ref(
        id=str(d.get("id", "")),
        kind=str(d.get("kind", "")),
        title=str(d.get("title", "")),
        source=str(d.get("source", "")),
        payload=d.get("payload") or {},
    )


def buildContextSummary(state: WorkbenchState) -> str:
    parts: list[str] = [f"질문: {state.question}"]
    if state.selectedSkillRefs:
        parts.append("선택된 skill: " + ", ".join(r.id for r in state.selectedSkillRefs))
    if state.apiRefs:
        parts.append("후보 API: " + ", ".join(r.id for r in state.apiRefs[:8]))
    if state.requiredEvidence:
        parts.append("requiredEvidence: " + ", ".join(state.requiredEvidence))
    if state.refs:
        parts.append(f"누적 ref: {len(state.refs)}개")
        sample = [f"{r.kind}:{r.id}" for r in state.refs[-10:]]
        parts.append("최근 ref 샘플: " + ", ".join(sample))
    if state.critiques:
        parts.append("CRITIQUE 이슈: " + "; ".join(c.get("text", "") for c in state.critiques[:5]))
    return "\n".join(parts)
