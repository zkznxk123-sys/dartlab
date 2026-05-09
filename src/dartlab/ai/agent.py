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
from .tool_storage import buildPersistedContent, exceedsSizeCap, persistLargeResult
from .tools.formatting import wrap_external_in_result
from .tools.registry import executeTool, toolSpecs
from .workbench.prompts import DARTLAB_CHAT_SYSTEM

logger = logging.getLogger(__name__)

# LLM 노출 도구 set — PascalCase (Claude 도구 체계 호환). Skill 우선 → Capability → 실행 → 시각화.
# EngineCall = 단일 capability 1 회. RunPython = 다단 계산. Read = 파일 직접 인용.
# RunWorkbench 는 5 패스 elevate 명시 경로 — feedback_no_graph_regression.md 정당 활성 경로 (2).
_DEFAULT_TOOL_NAMES: tuple[str, ...] = (
    "ReadSkill",
    "GetSkillBody",
    "ReadCapability",
    "EngineCall",
    "RunPython",
    "Read",
    "WebSearch",
    "SaveArtifact",
    "CompileVisual",
    "RunWorkbench",
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
    """본체 — chat-native autonomous tool-calling 루프. agent_gateway 가 본 함수의 TraceEvent 를 SSE 로 변환."""
    history = history or []
    system_prompt = _injectPastContextIfAvailable(DARTLAB_CHAT_SYSTEM, _unused)
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
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

    # chat-native 흐름은 phase (단계) 가 없다. 도구 카드 + 텍스트 streaming 이 모든 진행 표현.
    # 무의미한 graph_node 1 회 emit 은 UI groupActivities 가 잘못된 phase ("작성") 라벨 붙이게 만들어 제거.
    # 회귀 가드: memory/feedback_no_graph_regression.md.
    refs: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    text_emitted = ""
    # 같은 도구 + 같은 error 코드 누적 카운트. 임계 도달 시 도구 호출 차단 +
    # 다음 LLM turn 에 시스템 메시지로 "이 도구 그만 시도하고 답변 작성하라" 신호.
    # max_iterations 까지 무의미 retry 하다 답변 못 만드는 회귀 방지.
    failure_streak: dict[tuple[str, str], int] = {}
    blocked_tools: set[str] = set()
    _FAILURE_STREAK_LIMIT = 2
    # 동일 (name, args) 호출 결과 캐시 — LLM 이 같은 도구·인자를 반복하면 재실행하지 않고
    # cached 결과 즉시 반환 + LLM 메시지에 "이미 호출됐음, 다시 부르지 마라" 명시.
    # 사용자 audit 에서 ReadCapability 2 회 / 같은 Read 3 회 같은 비효율 루프 차단.
    call_cache: dict[tuple[str, str], dict[str, Any]] = {}

    for iteration in range(max_iterations):
        # 옛 assistant reasoning 트리밍 (마지막 2 개 외 content → None). tool_calls 보존.
        # 회귀 가드: 노드 추가 아님. 기계적 메모리 관리만.
        _microcompact(messages, keep_last=2)

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
                # 동일 도구가 임계 회 연속 실패한 적 있으면 호출 차단 + LLM 에 안내.
                if tc.name in blocked_tools:
                    yield TraceEvent(
                        "tool_start",
                        {"id": tc.id, "tool": tc.name, "input": tc.args, "summary": f"{tc.name} 차단됨"},
                    )
                    yield TraceEvent(
                        "tool_result",
                        {
                            "id": tc.id,
                            "tool": tc.name,
                            "status": "error",
                            "outputSummary": f"{tc.name} 반복 실패 — 호출 차단",
                            "evidenceRefs": [],
                            "artifacts": [],
                            "error": "tool_blocked_after_repeated_failures",
                            "data": None,
                        },
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(
                                {
                                    "ok": False,
                                    "summary": f"{tc.name} 가 직전 turn 에서 반복 실패해 차단됨. 본 도구 다시 호출 금지. 지금까지 모은 정보로 답변 작성하거나 다른 도구 사용.",
                                    "data": None,
                                    "error": "tool_blocked_after_repeated_failures",
                                },
                                ensure_ascii=False,
                            ),
                        }
                    )
                    continue
                yield TraceEvent(
                    "tool_start",
                    {
                        "id": tc.id,
                        "tool": tc.name,
                        "input": tc.args,
                        "summary": f"{tc.name} 호출",
                    },
                )
                # 동일 (name, args) 호출이 한 run 에서 반복되면 cached 결과 즉시 재사용.
                # LLM 에 "이미 호출됐음, 다시 부르지 마라" 명시 — 무의미 루프 차단.
                cache_key = (tc.name, json.dumps(tc.args or {}, ensure_ascii=False, sort_keys=True, default=str))
                cached = call_cache.get(cache_key)
                if cached is not None:
                    cached_summary = str(cached.get("summary") or "")
                    note = f"(cached) 같은 인자로 이미 호출됨 — 다시 부르지 마라. 직전 결과: {cached_summary[:120]}"
                    yield TraceEvent(
                        "tool_result",
                        {
                            "id": tc.id,
                            "tool": tc.name,
                            "status": "done" if cached.get("ok") else "error",
                            "outputSummary": note,
                            "evidenceRefs": [ref.get("id") for ref in cached.get("refs") or [] if ref.get("id")],
                            "artifacts": [r for r in cached.get("refs") or [] if r.get("kind") == "artifactRef"],
                            "error": cached.get("error"),
                            "data": cached.get("data"),
                            "cached": True,
                        },
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(
                                {
                                    "ok": cached.get("ok"),
                                    "summary": note,
                                    "data": None,
                                    "error": cached.get("error"),
                                },
                                ensure_ascii=False,
                            ),
                        }
                    )
                    continue
                result_dict = executeTool(tc.name, tc.args)
                call_cache[cache_key] = result_dict
                # 실패 streak 추적 — 같은 도구 + 같은 error 코드 N 회 → blocked.
                if not result_dict.get("ok"):
                    err_key = str(result_dict.get("error") or "unknown")
                    streak_key = (tc.name, err_key)
                    failure_streak[streak_key] = failure_streak.get(streak_key, 0) + 1
                    if failure_streak[streak_key] >= _FAILURE_STREAK_LIMIT:
                        blocked_tools.add(tc.name)
                else:
                    # 성공 시 해당 도구의 모든 streak 리셋.
                    failure_streak = {k: v for k, v in failure_streak.items() if k[0] != tc.name}
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
                        # raw data — agent_gateway._public_result_payload 가 stdout/values/table
                        # preview 추출. UI expand 시 표시.
                        "data": result_dict.get("data"),
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
                content_str = json.dumps(
                    {
                        "ok": wrapped.get("ok"),
                        "summary": wrapped.get("summary", ""),
                        "data": wrapped.get("data"),
                        "error": wrapped.get("error"),
                    },
                    ensure_ascii=False,
                    default=str,
                )
                # 큰 결과는 디스크 persist + preview 만 inject. LLM 이 Read 도구로 전체 재호출 가능.
                if exceedsSizeCap(content_str):
                    preview, file_path = persistLargeResult(tc.name, tc.id, content_str)
                    content_str = buildPersistedContent(file_path, preview, len(content_str))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": content_str,
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


def _injectPastContextIfAvailable(systemPrompt: str, kwargs: dict[str, Any]) -> str:
    """kwargs.stockCode 가 있으면 outcome_log past_context 를 system prompt 에 부착.

    빈 문자열이면 섹션 헤더 자체 부재 — 환각 가드 (CHANGELOG #572 패턴).
    """
    stock_code = kwargs.get("stockCode")
    if not stock_code:
        return systemPrompt
    market = kwargs.get("market") or "KR"
    try:
        from .memory.wiring import fetchPastContext

        past = fetchPastContext(str(stock_code), market=str(market))
    except Exception:  # noqa: BLE001
        past = ""
    if not past:
        return systemPrompt
    return f"{systemPrompt}\n\n## 과거 결정 회고 (참고 — 환각 금지, 위 사실에만 의존하라)\n{past}\n"


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
        stockCode=stock_code,
        market=market,
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


def _microcompact(messages: list[dict[str, Any]], *, keep_last: int = 2) -> None:
    """오래된 assistant message 의 reasoning content 를 None 으로 (in-place).

    tool_calls 구조는 보존 — provider 들이 tool result 매칭에 필요. 마지막 keep_last 개의
    assistant message 는 reasoning 유지 (직전 추론 흐름 단절 방지).

    회귀 가드: graph 노드 추가 아님. messages 배열 트리밍만.
    memory/feedback_no_graph_regression.md 6 패턴과 무관.
    """
    ai_indices = [i for i, msg in enumerate(messages) if isinstance(msg, dict) and msg.get("role") == "assistant"]
    if len(ai_indices) <= keep_last:
        return
    for idx in ai_indices[:-keep_last]:
        msg = messages[idx]
        if msg.get("tool_calls") and msg.get("content"):
            msg["content"] = None


__all__ = ["runAgent"]
