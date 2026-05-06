"""5 패스 공용 LLM-도구 루프 (옛 WorkbenchProvider / generate() 시스템).

provider.generate(messages, tools) -> ProviderTurn 호출 + tool_calls 실행 + tool_result 메시지 이어붙여 다음 라운드.

안전성:
- tool_result content 가 _MAX_TOOL_RESULT_CHARS 초과면 truncate.
- 누적 messages 가 _MAX_MESSAGES_CHARS 초과면 가장 오래된 tool 메시지부터 trim.
- provider.generate() RateLimitError 면 1 회 retry.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import Ref, TraceEvent
from dartlab.ai.providers import ProviderTurn, WorkbenchProvider
from dartlab.ai.providers.base import RateLimitError
from dartlab.ai.tools.registry import _SPECS as TOOL_SPECS
from dartlab.ai.tools.registry import executeTool

from .state import WorkbenchState

_MAX_TOOL_RESULT_CHARS = int(os.environ.get("DARTLAB_TOOL_RESULT_MAX_CHARS", "8000"))
_MAX_MESSAGES_CHARS = int(os.environ.get("DARTLAB_MESSAGES_MAX_CHARS", "120000"))
_RATE_LIMIT_RETRY_DELAY_SEC = float(os.environ.get("DARTLAB_RATE_LIMIT_RETRY_SEC", "2"))


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
        _trimMessagesIfNeeded(messages)
        try:
            turn = _generateWithRetry(provider, messages, tools_payload)
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
            content = json.dumps(result, ensure_ascii=False, default=str)
            if len(content) > _MAX_TOOL_RESULT_CHARS:
                content = content[:_MAX_TOOL_RESULT_CHARS] + f"\n...(truncated, full {len(content)} chars)"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": content,
                }
            )

    yield TraceEvent(kind="pass_exit", data={"pass": passName, "rounds": rounds_used})


def _generateWithRetry(
    provider: WorkbenchProvider, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> ProviderTurn:
    """provider.generate() — RateLimitError 1 회 retry."""
    try:
        return provider.generate(messages, tools)
    except RateLimitError:
        time.sleep(_RATE_LIMIT_RETRY_DELAY_SEC)
        return provider.generate(messages, tools)


def _trimMessagesIfNeeded(messages: list[dict[str, Any]]) -> None:
    """누적 messages 가 한도를 넘으면 가장 오래된 tool 메시지부터 trim.

    system / user (첫 두 개) 와 마지막 assistant 는 보존. 그 사이 tool 메시지를 우선 제거.
    """
    total = sum(len(str(m.get("content") or "")) for m in messages)
    if total <= _MAX_MESSAGES_CHARS:
        return
    # 보존 인덱스: 0 (system), 1 (user), 마지막 메시지
    if len(messages) <= 3:
        return
    keep_head = 2
    keep_tail = 1
    middle = messages[keep_head : len(messages) - keep_tail]
    # tool 메시지 우선 제거
    middle_filtered = [m for m in middle if m.get("role") != "tool"]
    new_total = sum(
        len(str(m.get("content") or "")) for m in messages[:keep_head] + middle_filtered + messages[-keep_tail:]
    )
    if new_total <= _MAX_MESSAGES_CHARS:
        messages[keep_head : len(messages) - keep_tail] = middle_filtered
        return
    # tool 제거로도 부족하면 가장 오래된 assistant 부터 truncate
    while middle_filtered and new_total > _MAX_MESSAGES_CHARS:
        middle_filtered.pop(0)
        new_total = sum(
            len(str(m.get("content") or "")) for m in messages[:keep_head] + middle_filtered + messages[-keep_tail:]
        )
    messages[keep_head : len(messages) - keep_tail] = middle_filtered


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
    recipe_lines = _formatRecipeSteps(state.selectedSkillRefs)
    if recipe_lines:
        parts.append("선택 recipe 의 단계 (순차 실행):\n" + recipe_lines)
    if state.refs:
        parts.append(f"누적 ref: {len(state.refs)}개")
        sample = [f"{r.kind}:{r.id}" for r in state.refs[-10:]]
        parts.append("최근 ref 샘플: " + ", ".join(sample))
    if state.critiques:
        parts.append("CRITIQUE 이슈: " + "; ".join(c.get("text", "") for c in state.critiques[:5]))
    return "\n".join(parts)


def _formatRecipeSteps(refs: list[Ref]) -> str:
    """selectedSkillRefs 중 recipe ref 의 step list 직렬화.

    형식: "1. {skillId} — {note}\\n2. ...". step 당 60 char truncate, max 8 step.
    """
    for ref in refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        if payload.get("kind") != "recipe" and not payload.get("recipeSteps"):
            continue
        steps = payload.get("recipeSteps") or []
        if not steps:
            from dartlab.skills.registry import _steps_from_recipe_body

            steps = _steps_from_recipe_body(str(payload.get("body") or ""))
        if not steps:
            steps = [{"skillId": sid, "note": ""} for sid in payload.get("linkedSkills") or []]
        if not steps:
            continue
        lines: list[str] = []
        for index, step in enumerate(steps[:8], start=1):
            skill_id = str(step.get("skillId") or "")
            note = str(step.get("note") or "")
            entry = f"{index}. {skill_id}"
            if note:
                entry += f" — {note[:60]}"
            lines.append(entry)
        return "\n".join(lines)
    return ""
