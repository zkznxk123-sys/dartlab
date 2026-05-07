"""DartLab AI 본체 — chat-native + LLM 자율 tool calling. Cursor/Aider 패턴.

agent_gateway 가 호출. 흐름:

```
loop (max 8 iter):
    turn = stream_provider(provider, messages, tools)   # text 델타 streaming
    if turn.tool_calls:
        for tc: execute(tc); messages.append(tool_result)
        continue
    final text → done
```

5 패스 graph 와 다른 점:
- 흐름 강제 X. LLM 이 *언제 어떤 도구* 자율 결정.
- workbench 5 패스는 *옵션 sub-agent*. 본 모듈이 본체.

회귀 방지: memory/feedback_no_graph_regression.md 참조. BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST
같은 *고정 노드 강제* 패턴을 본 모듈에 추가 금지. 새 능력은 ai/tools/ 안에서.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from .contracts import TraceEvent
from .providers import stream_provider
from .tools.formatting import wrap_external_in_result
from .tools.registry import executeTool, toolSpecs
from .workbench.prompts import DARTLAB_CHAT_SYSTEM

logger = logging.getLogger(__name__)

# LLM 노출 도구 set — SSOT P-revised canonical 6 데이터 도구 + 1 meta (run_workbench).
# `engine_call` 은 `run_python` 안에서 임의 dartlab 호출로 통합되어 폐기됨.
# run_workbench 는 5 패스 elevate 명시 경로 — feedback_no_graph_regression.md 정당 활성 경로 (2).
_DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "run_python",
    "read_skill",
    "read_capability",
    "web_search",
    "save_artifact",
    "compile_visual",
    "run_workbench",
)


def runAgent(
    question: str,
    *,
    provider: Any,
    history: list[dict[str, Any]] | None = None,
    tool_names: tuple[str, ...] = _DEFAULT_TOOL_NAMES,
    max_iterations: int = 8,
    **_unused: Any,
) -> Iterator[TraceEvent]:
    """본체 — LLM 자율 tool calling 루프. agent_gateway 가 본 함수의 TraceEvent 를 SSE 로 변환."""
    history = history or []
    messages: list[dict[str, Any]] = [{"role": "system", "content": DARTLAB_CHAT_SYSTEM}]
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content") or entry.get("text") or ""
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})
    user_text = str(question or "").strip()
    if user_text:
        messages.append({"role": "user", "content": user_text})

    tools = _selectTools(tool_names)

    yield TraceEvent("graph_node", {"node": "agent", "summary": "응답 생성 중", "status": "running"})

    refs: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    text_emitted = ""

    for iteration in range(max_iterations):
        try:
            chunks = list(stream_provider(provider, messages, tools))
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "stream_provider failed (provider=%s, iter=%d)",
                getattr(getattr(provider, "config", None), "provider", "?"),
                iteration,
            )
            yield TraceEvent("error", {"error": f"{type(exc).__name__}: {exc}"})
            return

        # 텍스트 델타 emit (final 아닌 chunks)
        for chunk in chunks:
            if chunk.text and not chunk.final:
                text_emitted += chunk.text
                yield TraceEvent("chunk", {"text": chunk.text})

        final_chunk = next((c for c in chunks if c.final), None)
        turn = final_chunk.turn if final_chunk else None
        if turn is None:
            yield TraceEvent("error", {"error": "no_final_turn"})
            return

        if turn.tool_calls:
            # streaming 미지원 provider 가 final 만 emit 하면 turn.content 가 그대로 텍스트일 수 있음.
            # 단 tool_calls 가 있으면 사용자에게 텍스트보다 도구 결과가 본체 — 텍스트는 일단 보존.
            if turn.content and not text_emitted:
                text_emitted = turn.content
                for piece in _chunks(turn.content, size=64):
                    yield TraceEvent("chunk", {"text": piece})

            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": turn.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.args, ensure_ascii=False),
                        },
                    }
                    for tc in turn.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in turn.tool_calls:
                yield TraceEvent(
                    "tool_start",
                    {
                        "id": tc.id,
                        "tool": tc.name,
                        "input": tc.args,
                        "summary": f"{tc.name} 호출",
                    },
                )
                result_dict = executeTool(tc.name, tc.args)
                tool_refs = list(result_dict.get("refs") or [])
                refs.extend(tool_refs)
                tool_artifacts = [ref for ref in tool_refs if ref.get("kind") == "artifactRef"]
                artifacts.extend(tool_artifacts)
                yield TraceEvent(
                    "tool_result",
                    {
                        "id": tc.id,
                        "tool": tc.name,
                        "status": "done" if result_dict.get("ok") else "error",
                        "outputSummary": result_dict.get("summary", ""),
                        "evidenceRefs": [ref.get("id") for ref in tool_refs if ref.get("id")],
                        "artifacts": tool_artifacts,
                        "error": result_dict.get("error"),
                    },
                )
                # visualRef 발견 시 VIEW_SPEC event emit — ChartRenderer 가 메시지 흐름에 인라인.
                for ref in tool_refs:
                    if ref.get("kind") != "visualRef":
                        continue
                    payload = ref.get("payload") or {}
                    spec = payload.get("spec") if isinstance(payload, dict) else None
                    if not spec:
                        continue
                    yield TraceEvent(
                        "view_spec",
                        {
                            "id": ref.get("id"),
                            "spec": spec,
                            "title": ref.get("title"),
                            "source": ref.get("source"),
                        },
                    )
                # 외부 본문 (sourceType=external) 인 ref 가 있으면 data 텍스트 필드를 [EXTERNAL CONTENT START/END]
                # 마커로 감싼다 — LLM 이 마커 안의 지시를 *데이터* 로만 다루게 한다.
                # 상세: runtime.workbenchEvidenceFlow "외부 본문 처리".
                wrapped = wrap_external_in_result(result_dict)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {
                                "ok": wrapped.get("ok"),
                                "summary": wrapped.get("summary", ""),
                                "data": wrapped.get("data"),
                                "error": wrapped.get("error"),
                            },
                            ensure_ascii=False,
                        ),
                    }
                )
            continue  # 다시 LLM 호출

        # tool_calls 없음 → 최종 답변
        if not text_emitted and turn.content:
            # streaming 미지원 provider 가 final.turn.content 에 전체 텍스트
            text_emitted = turn.content
            for piece in _chunks(turn.content, size=64):
                yield TraceEvent("chunk", {"text": piece})
        break
    else:
        yield TraceEvent("error", {"error": "max_iterations_reached"})
        return

    # chat-native HARVEST bridge — workbench HARVEST 와 동일 helper 로 memory 작성.
    # SSOT.md Principle 6 정합 (모든 종료 경로 → decisions.jsonl + skill_stats.jsonl).
    _wireChatNativeMemory(
        question=user_text,
        answerText=text_emitted,
        refs=refs,
        kwargs=_unused,
    )

    yield TraceEvent(
        "done",
        {
            "refs": refs,
            "artifacts": artifacts,
            "verification": {"ok": True, "issues": [], "refId": "verify:answer"},
            "responseMeta": {
                "finalEvent": "answer",
                "responseStatus": "ok",
                "refCount": len(refs),
                "passes": ["agent", "memory"],
                "mode": "agent",
            },
        },
    )


def _wireChatNativeMemory(
    *, question: str, answerText: str, refs: list[dict[str, Any]], kwargs: dict[str, Any]
) -> None:
    """agent.py 종료 시 memory wiring — workbench/harvest.py 와 동일 helper 사용."""
    from .contracts import Ref
    from .memory.wiring import inferStockCodeContext, wireSessionMemory

    ref_objects: list[Ref] = []
    for raw in refs:
        if not isinstance(raw, dict):
            continue
        ref_objects.append(
            Ref(
                id=str(raw.get("id") or ""),
                kind=str(raw.get("kind") or ""),
                title=str(raw.get("title") or ""),
                source=str(raw.get("source") or ""),
                payload=raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
            )
        )

    extra_tags: list[str] = []
    stock_code, market = inferStockCodeContext(ref_objects, kwargs=kwargs)
    if stock_code:
        extra_tags.append(f"target:{stock_code}")
    if market:
        extra_tags.append(f"market:{market}")

    wireSessionMemory(
        question=question,
        answerText=answerText,
        refs=ref_objects,
        selectedSkillRefs=(r for r in ref_objects if r.kind == "skillRef"),
        ok=True,
        extraTags=extra_tags,
    )


def _selectTools(tool_names: tuple[str, ...]) -> list[dict[str, Any]]:
    """toolSpecs() raw dict ({name, description, inputSchema}) → OpenAI function calling 형식.

    각 provider 가 자체 toolSchema 변환 가지면 호출자가 별도 처리. 본 helper 는 OpenAI 호환만.
    """
    allowed = set(tool_names)
    out: list[dict[str, Any]] = []
    for spec in toolSpecs():
        if not isinstance(spec, dict):
            continue
        name = spec.get("name")
        if name not in allowed:
            continue
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": spec.get("description", ""),
                    "parameters": spec.get("inputSchema", {"type": "object", "properties": {}}),
                },
            }
        )
    return out


def _chunks(text: str, *, size: int = 240) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]


__all__ = ["runAgent"]
