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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .contracts import TraceEvent
from .providers import streamProvider
from .tools.formatting import wrapExternalInResult
from .tools.registry import executeTool, isToolReadOnly, toolSpecs
from .toolStorage import buildPersistedContent, exceedsSizeCap, persistLargeResult
from .workbench.prompts import DARTLAB_CHAT_SYSTEM

logger = logging.getLogger(__name__)

# 한 turn 에 LLM 이 동시에 emit 한 read-only 도구들을 thread pool 로 fan-out.
# 같은 turn 안 호출은 LLM 이 의존성 없음을 보증 (의존 있으면 다른 turn 으로 분리). 즉
# ReadSkill + ReadCapability + InspectDataset + EngineCall(scan='roe') + EngineCall(scan='debt')
# 같은 묶음은 모두 동시 실행 가능. write 도구 (RunPython · SaveArtifact · OutcomeLog) 는 시퀀셜.
#
# 워커 수 4 — polars/Rust 가 GIL 풀어 CPU bound 도 진짜 병렬, 네트워크 외부 호출 (WebSearch) 도
# 함께 묶임. 8 까지 늘려도 안전하나 LLM provider rate-limit 측면에서 보수적.
_PARALLEL_READ_WORKERS = 4

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
    "CreateUserSkill",
    "CompileVisual",
    # finance-native primitive (Track C/G/H/I) — registry 등록만 됐다가 default 미노출
    # 이라 LLM 이 호출 못 했던 회귀. 2026-05-17 OAuth probe 에서 다중 종목 비교 시
    # CompareCompanies 1 회 대신 Company.show 2 회 + RunPython 우회 (91s) 발견 후 합류.
    "CompareCompanies",
    "PickStoryTemplate",
    "EvidenceGate",
    "GroundingCheck",
    "RunWorkbench",
    # 과거 세션 transcript cross-session 검색 — "이 회사 분석한 적 있나" / "이 매핑 결정
    # 어디서 했지" 류 질문에서 LLM 자율 호출. BM25 + FTS5 (sessionIndex.db ~/.dartlab/).
    "SearchPastSessions",
)


def runAgent(
    question: str,
    *,
    provider: Any,
    history: list[dict[str, Any]] | None = None,
    toolNames: tuple[str, ...] = _DEFAULT_TOOL_NAMES,
    maxIterations: int = 30,
    **_unused: Any,
) -> Iterator[TraceEvent]:
    """본체 — chat-native autonomous tool-calling 루프. agent_gateway 가 본 함수의 TraceEvent 를 SSE 로 변환."""
    history = history or []
    systemPrompt = _injectPastContextIfAvailable(DARTLAB_CHAT_SYSTEM, _unused)
    messages: list[dict[str, Any]] = [{"role": "system", "content": systemPrompt}]
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content") or entry.get("text") or ""
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": str(content)})
    userText = str(question or "").strip()
    if userText:
        messages.append({"role": "user", "content": userText})

    tools = _selectTools(toolNames)

    # chat-native 흐름은 phase (단계) 가 없다. 도구 카드 + 텍스트 streaming 이 모든 진행 표현.
    # 무의미한 graph_node 1 회 emit 은 UI groupActivities 가 잘못된 phase ("작성") 라벨 붙이게 만들어 제거.
    # 회귀 가드: memory/feedback_no_graph_regression.md.
    refs: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    text_emitted = ""
    # 실패 streak — 같은 (도구, error code, args) 가 임계 회 누적되면 그 *args 만* 차단.
    # 과거 (도구, error) 단위 차단은 한 호출의 invalid args 때문에 다른 valid args 도 막혔던
    # 회귀 (2026-05-17): EngineCall("macro.rates") → unknown_api_ref → EngineCall("gather.macro") →
    # unknown_api_ref → EngineCall("macro") (valid) 차단. 도구 전체 막지 말고 args 만.
    failure_streak: dict[tuple[str, str, str], int] = {}
    blocked_calls: set[tuple[str, str]] = set()  # (name, argsHash)
    _FAILURE_STREAK_LIMIT = 2
    # 동일 (name, args) 호출 결과 캐시 — LLM 이 같은 도구·인자를 반복하면 재실행하지 않고
    # cached 결과 즉시 반환 + LLM 메시지에 "이미 호출됐음, 다시 부르지 마라" 명시.
    # 사용자 audit 에서 ReadCapability 2 회 / 같은 Read 3 회 같은 비효율 루프 차단.
    call_cache: dict[tuple[str, str], dict[str, Any]] = {}
    # 같은 (name, args) 가 cache_hit 임계 회 반복되면 강제 차단 — LLM 이 자연어 가드 무시하고
    # 계속 부르는 회귀 (사용자 audit: scan.ratio 4 회 연속 cached) 방지.
    cache_hit_count: dict[tuple[str, str], int] = {}
    _CACHE_HIT_BLOCK_LIMIT = 2

    for iteration in range(maxIterations):
        # 옛 assistant reasoning 트리밍 (마지막 2 개 외 content → None). tool_calls 보존.
        # 회귀 가드: 노드 추가 아님. 기계적 메모리 관리만.
        _microcompact(messages, keepLast=2)

        # lazy 소비 — provider 가 토큰 yield 하는 즉시 SSE chunk emit (typing 효과).
        # 회귀 가드: list(streamProvider(...)) 로 한 번에 모은 뒤 풀면 LLM 응답 끝까지 블록 →
        # UI 가 "분석중..." 만 길게 보이다 한 방에 답이 나타남. iterator 그대로 돌려야 한다.
        final_chunk = None
        try:
            for chunk in streamProvider(provider, messages, tools):
                if chunk.final:
                    final_chunk = chunk
                    continue
                if chunk.text:
                    text_emitted += chunk.text
                    yield TraceEvent("chunk", {"text": chunk.text})
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "stream_provider failed (provider=%s, iter=%d)",
                getattr(getattr(provider, "config", None), "provider", "?"),
                iteration,
            )
            yield TraceEvent("error", {"error": f"{type(exc).__name__}: {exc}"})
            return

        turn = final_chunk.turn if final_chunk else None
        if turn is None:
            yield TraceEvent("error", {"error": "no_final_turn"})
            return

        if turn.toolCalls:
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
                    for tc in turn.toolCalls
                ],
            }
            messages.append(assistant_msg)

            # ── 2 단 fan-out: read-only 병렬 + write 시퀀셜 ──
            # turn 안 toolCalls 는 LLM 이 의존성 없음 보증 (의존 있으면 다른 turn 분리).
            # blocked / cached path 는 외부 호출 0 ms 라 분류 후 즉시 emit. 새 실행만 partition.
            fresh_read: list[tuple[Any, tuple[str, str]]] = []
            fresh_write: list[tuple[Any, tuple[str, str]]] = []
            for tc in turn.toolCalls:
                cache_key = (
                    tc.name,
                    json.dumps(tc.args or {}, ensure_ascii=False, sort_keys=True, default=str),
                )
                if cache_key in blocked_calls:
                    yield from _emitBlocked(tc, messages)
                    continue
                cached = call_cache.get(cache_key)
                if cached is not None:
                    cache_hit_count[cache_key] = cache_hit_count.get(cache_key, 0) + 1
                    yield from _emitCached(tc, cached, cache_hit_count[cache_key], _CACHE_HIT_BLOCK_LIMIT, messages)
                    continue
                (fresh_read if isToolReadOnly(tc.name) else fresh_write).append((tc, cache_key))

            # Phase 2: read-only 병렬 — tool_start 모두 즉시 + as_completed 로 결과 도착순 emit.
            if fresh_read:
                for tc, _ in fresh_read:
                    yield TraceEvent(
                        "tool_start",
                        {"id": tc.id, "tool": tc.name, "input": tc.args, "summary": f"{tc.name} 호출"},
                    )
                # 작업 단위 함수 (thread 안에서 호출). registry.executeTool 자체는 thread-safe —
                # 각 도구가 자체 캐시/IO 만 건드리고 agent.py 의 mutable state 는 메인 thread 만 변경.
                with ThreadPoolExecutor(max_workers=_PARALLEL_READ_WORKERS) as ex:
                    fut_to_meta = {
                        ex.submit(executeTool, tc.name, tc.args): (tc, cache_key) for tc, cache_key in fresh_read
                    }
                    for fut in as_completed(fut_to_meta):
                        tc, cache_key = fut_to_meta[fut]
                        try:
                            resultDict = fut.result()
                        except Exception as exc:  # noqa: BLE001
                            logger.exception("tool %s threw uncaught (parallel)", tc.name)
                            resultDict = {
                                "ok": False,
                                "summary": f"{tc.name} 실행 오류: {type(exc).__name__}",
                                "data": None,
                                "error": type(exc).__name__,
                                "refs": [],
                            }
                        call_cache[cache_key] = resultDict
                        yield from _finalizeResult(
                            tc,
                            cache_key,
                            resultDict,
                            refs,
                            artifacts,
                            failure_streak,
                            blocked_calls,
                            messages,
                            failureStreakLimit=_FAILURE_STREAK_LIMIT,
                        )

            # Phase 3: write 시퀀셜 — 순서 의존 가능 (SaveArtifact 덮어쓰기 등).
            for tc, cache_key in fresh_write:
                yield TraceEvent(
                    "tool_start",
                    {"id": tc.id, "tool": tc.name, "input": tc.args, "summary": f"{tc.name} 호출"},
                )
                try:
                    resultDict = executeTool(tc.name, tc.args)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("tool %s threw uncaught (sequential)", tc.name)
                    resultDict = {
                        "ok": False,
                        "summary": f"{tc.name} 실행 오류: {type(exc).__name__}",
                        "data": None,
                        "error": type(exc).__name__,
                        "refs": [],
                    }
                call_cache[cache_key] = resultDict
                yield from _finalizeResult(
                    tc,
                    cache_key,
                    resultDict,
                    refs,
                    artifacts,
                    failure_streak,
                    blocked_calls,
                    messages,
                    failureStreakLimit=_FAILURE_STREAK_LIMIT,
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
        # max_iterations 도달 → graceful finalize. 에러로 죽이지 않고, tools=[] 로
        # 마지막 1 회 turn 강제 — 지금까지 쌓인 tool 결과 컨텍스트로 답안 작성.
        # 근거 부족은 답안 안에서 한계로 명시. 무한 도구 루프 차단 + 부분 답 보장.
        messages.append(
            {
                "role": "user",
                "content": (
                    "도구 호출 한도에 도달했습니다. 추가 도구 호출 없이 지금까지 "
                    "수집한 결과로 사용자 질문에 답을 작성하세요. 근거 부족 부분은 "
                    "솔직히 한계로 명시하고, 가능한 범위에서 답을 정리하세요."
                ),
            }
        )
        final_chunk = None
        try:
            for chunk in streamProvider(provider, messages, []):
                if chunk.final:
                    final_chunk = chunk
                    continue
                if chunk.text:
                    text_emitted += chunk.text
                    yield TraceEvent("chunk", {"text": chunk.text})
        except Exception as exc:  # noqa: BLE001
            logger.exception("max_iterations finalize failed")
            yield TraceEvent("error", {"error": f"max_iterations_finalize_failed: {exc}"})
            return
        if final_chunk and not text_emitted and getattr(final_chunk, "turn", None) and final_chunk.turn.content:
            text_emitted = final_chunk.turn.content
            for piece in _chunks(text_emitted, size=64):
                yield TraceEvent("chunk", {"text": piece})

    # chat-native HARVEST bridge — workbench HARVEST 와 동일 helper 로 memory 작성.
    # SSOT.md Principle 6 정합 (모든 종료 경로 → decisions.jsonl + skill_stats.jsonl).
    _wireChatNativeMemory(
        question=userText,
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


def _emitBlocked(tc: Any, messages: list[dict[str, Any]]) -> Iterator[TraceEvent]:
    """차단된 도구 호출 — tool_start + tool_result(error) + tool message 한 묶음 emit."""
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


def _emitCached(
    tc: Any,
    cached: dict[str, Any],
    hitN: int,
    hitBlockLimit: int,
    messages: list[dict[str, Any]],
) -> Iterator[TraceEvent]:
    """cached 호출 — 동일 (name, args) 재호출 시 즉시 응답. hitBlockLimit 초과 시 강제 차단."""
    yield TraceEvent(
        "tool_start",
        {"id": tc.id, "tool": tc.name, "input": tc.args, "summary": f"{tc.name} 호출"},
    )
    is_blocked = hitN >= hitBlockLimit
    cached_summary = str(cached.get("summary") or "")
    if is_blocked:
        llmGuardNote = (
            f"{tc.name} 가 같은 인자로 {hitN} 회 반복 호출됨 — 본 인자 재호출 영구 차단. "
            f"다른 도구나 답변 작성으로 진행."
        )
    else:
        llmGuardNote = f"(cached) 같은 인자로 이미 호출됨 — 다시 부르지 마라. 직전 결과: {cached_summary[:120]}"
    uiSummary = f"(반복 차단) 같은 인자 {hitN} 회 — 더 부르지 않음" if is_blocked else f"(캐시됨) {cached_summary[:80]}"
    yield TraceEvent(
        "tool_result",
        {
            "id": tc.id,
            "tool": tc.name,
            "status": "done" if cached.get("ok") and not is_blocked else "error",
            "outputSummary": uiSummary,
            "evidenceRefs": [ref.get("id") for ref in cached.get("refs") or [] if ref.get("id")],
            "artifacts": [r for r in cached.get("refs") or [] if r.get("kind") == "artifactRef"],
            "error": cached.get("error") if not is_blocked else "duplicate_cache_call_blocked",
            "data": cached.get("data") if not is_blocked else None,
            "cached": True,
        },
    )
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(
                {
                    "ok": cached.get("ok") if not is_blocked else False,
                    "cached": True,
                    "summary": llmGuardNote,
                    "data": None,
                    "error": cached.get("error") if not is_blocked else "duplicate_cache_call_blocked",
                },
                ensure_ascii=False,
            ),
        }
    )


def _finalizeResult(
    tc: Any,
    cacheKey: tuple[str, str],
    resultDict: dict[str, Any],
    refs: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    failureStreak: dict[tuple[str, str, str], int],
    blockedCalls: set[tuple[str, str]],
    messages: list[dict[str, Any]],
    failureStreakLimit: int,
) -> Iterator[TraceEvent]:
    """새 실행 결과 후처리 — streak 갱신 + tool_result emit + visualRef view_spec + tool message append.

    메인 thread 에서만 호출 (read-only fan-out 의 as_completed 콜백 포함 — fut.result() 후 메인 generator
    가 본 함수 호출). thread 안에서는 호출 금지 — 공유 state mutation 있음.

    실패 streak partition: (name, error_code, argsHash) — 같은 도구의 valid 호출까지 차단되는
    회귀 (2026-05-17) 방지. blockedCalls 도 (name, argsHash) 단위로 — 도구 자체는 풀어둠.
    """
    argsHash = cacheKey[1]
    if not resultDict.get("ok"):
        err_key = str(resultDict.get("error") or "unknown")
        streak_key = (tc.name, err_key, argsHash)
        failureStreak[streak_key] = failureStreak.get(streak_key, 0) + 1
        if failureStreak[streak_key] >= failureStreakLimit:
            blockedCalls.add(cacheKey)
    else:
        # 같은 도구 + 같은 args 성공 → 그 args 의 모든 error streak 리셋.
        for k in [k for k in failureStreak if k[0] == tc.name and k[2] == argsHash]:
            failureStreak.pop(k, None)
    tool_refs = list(resultDict.get("refs") or [])
    refs.extend(tool_refs)
    tool_artifacts = [ref for ref in tool_refs if ref.get("kind") == "artifactRef"]
    artifacts.extend(tool_artifacts)
    yield TraceEvent(
        "tool_result",
        {
            "id": tc.id,
            "tool": tc.name,
            "status": "done" if resultDict.get("ok") else "error",
            "outputSummary": resultDict.get("summary", ""),
            "evidenceRefs": [ref.get("id") for ref in tool_refs if ref.get("id")],
            "refDetails": tool_refs,
            "artifacts": tool_artifacts,
            "error": resultDict.get("error"),
            "data": resultDict.get("data"),
        },
    )
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
    wrapped = wrapExternalInResult(resultDict)
    # refs 는 ref id + kind + title + source + payload 핵심 키만 직렬화 — token 절약하면서
    # 답변 inline 인용에 필요한 최소 정보 (id, source 식별자) 는 보존.
    # 회귀 가드: refs 누락 시 LLM 이 답변 본문에 [ref:...] 박을 수 없어 refs=0 답변.
    wrapped_refs = wrapped.get("refs") or []
    refs_for_llm = [
        {
            "id": r.get("id"),
            "kind": r.get("kind"),
            "title": r.get("title"),
            "source": r.get("source"),
            "sourceType": r.get("sourceType", "internal"),
            **({"payload": _trimRefPayload(r.get("payload") or {})} if r.get("payload") else {}),
        }
        for r in wrapped_refs
        if isinstance(r, dict) and r.get("id")
    ]
    content_str = json.dumps(
        {
            "ok": wrapped.get("ok"),
            "summary": wrapped.get("summary", ""),
            "data": wrapped.get("data"),
            "refs": refs_for_llm,
            "error": wrapped.get("error"),
        },
        ensure_ascii=False,
        default=str,
    )
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


_REF_PAYLOAD_KEYS = (
    "stockCode",
    "period",
    "metric",
    "value",
    "unit",
    "docId",
    "page",
    "lineStart",
    "lineEnd",
    "confidence",
    "dataAsOf",
    "axis",
    "axisKr",
    "stmt",
)


def _trimRefPayload(payload: dict[str, Any]) -> dict[str, Any]:
    """ref.payload 에서 LLM 인용에 필요한 핵심 키만 유지 — token 절약.

    핵심 키 (`stockCode` · `period` · `metric` · `value` · `docId` · `page` · `confidence` 등)
    만 유지. 나머지 (예: 5MB raw DataFrame 직렬화) 는 drop. LLM 은 ref id 로 inline 인용,
    상세 본문은 UI 가 별도 fetch.
    """
    return {k: payload[k] for k in _REF_PAYLOAD_KEYS if k in payload}


def _injectPastContextIfAvailable(systemPrompt: str, kwargs: dict[str, Any]) -> str:
    """kwargs 의 보조 컨텍스트를 system prompt 에 부착.

    두 블록 추가 가능:
        1. stockCode 가 있으면 outcome_log past_context (CHANGELOG #572 패턴)
            진입 직전 tryResolvePending lazy sweep 으로 pending → resolved 자동 전이 후 회수.
        2. dashboardSnapshot 이 있으면 "현재 화면" 블록 (Phase 8 bridge)

    빈 문자열이면 섹션 헤더 자체 부재 — 환각 가드.
    """
    stockCode = kwargs.get("stockCode")
    if stockCode:
        market = kwargs.get("market") or "KR"
        try:
            from .memory.wiring import defaultPriceLookup, fetchPastContext, tryResolvePending

            # 진입 lazy resolve — 해당 종목 pending 중 minHoldingDays 충족 entry 가
            # 있으면 시장 종가로 alpha 산출 후 resolved 전이. 다음 fetchPastContext
            # 호출이 *방금 resolved* 된 entry 까지 회수하도록 *resolve 먼저, fetch 다음* 순서.
            try:
                tryResolvePending(
                    str(stockCode),
                    market=str(market),
                    pricer=defaultPriceLookup if str(market) == "KR" else None,
                )
            except Exception:  # noqa: BLE001
                pass

            past = fetchPastContext(str(stockCode), market=str(market))
        except Exception:  # noqa: BLE001
            past = ""
        if past:
            systemPrompt = f"{systemPrompt}\n\n## 과거 결정 회고 (참고 — 환각 금지, 위 사실에만 의존하라)\n{past}\n"

    snapshot = kwargs.get("dashboardSnapshot")
    if isinstance(snapshot, dict):
        block = _formatDashboardSnapshotBlock(snapshot)
        if block:
            systemPrompt = f"{systemPrompt}\n\n## 현재 대시보드 화면 (사용자 시야, 신뢰)\n{block}\n"

    # 운영자 톤 메타 블록 — feedback_*.md 합성기가 7 일 TTL 또는 memory mtime 변경 시
    # 재계산. 답변 톤 일관성 확보 (자동 sweep 회피·운영자 명시 트리거·측정 후 박기).
    # 캐시 hit 시 디스크 1 회 read 만 — turn 추가 비용 최소.
    try:
        from .memory.synthesizer import buildToneBlock

        tone_block = buildToneBlock()
    except Exception:  # noqa: BLE001
        tone_block = ""
    if tone_block:
        systemPrompt = f"{systemPrompt}\n\n{tone_block}"

    return systemPrompt


def _formatDashboardSnapshotBlock(snapshot: dict[str, Any]) -> str:
    """dashboardStore.snapshot() 페이로드를 markdown bullet 으로 변환.

    페이로드 shape: {dashboardView, stockCode, axis, period, visibleKpis: [...]}
    사용자 시야 데이터라 외부 untrusted 마커 없이 trusted block 으로 삽입.
    """
    lines: list[str] = []
    view = snapshot.get("dashboardView")
    if view:
        lines.append(f"- 탭: `{view}`")
    code = snapshot.get("stockCode")
    if code:
        lines.append(f"- 회사: `{code}`")
    axis = snapshot.get("axis")
    if axis:
        lines.append(f"- 분석 axis: `{axis}`")
    period = snapshot.get("period")
    if period:
        lines.append(f"- 기간: `{period}`")
    kpis = snapshot.get("visibleKpis")
    if isinstance(kpis, list) and kpis:
        kpi_strs = []
        for kpi in kpis:
            if isinstance(kpi, dict) and "name" in kpi and "value" in kpi:
                kpi_strs.append(f"{kpi['name']}={kpi['value']}")
            else:
                kpi_strs.append(str(kpi))
        if kpi_strs:
            lines.append(f"- 보이는 KPI: {', '.join(kpi_strs)}")
    return "\n".join(lines)


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
    stockCode, market = inferStockCodeContext(ref_objects, kwargs=kwargs)
    if stockCode:
        extra_tags.append(f"target:{stockCode}")
    if market:
        extra_tags.append(f"market:{market}")

    wireSessionMemory(
        question=question,
        answerText=answerText,
        refs=ref_objects,
        selectedSkillRefs=(r for r in ref_objects if r.kind == "skillRef"),
        ok=True,
        extraTags=extra_tags,
        stockCode=stockCode,
        market=market,
    )


def _selectTools(toolNames: tuple[str, ...]) -> list[dict[str, Any]]:
    """toolSpecs() raw dict ({name, description, inputSchema}) → OpenAI function calling 형식.

    각 provider 가 자체 toolSchema 변환 가지면 호출자가 별도 처리. 본 helper 는 OpenAI 호환만.
    """
    allowed = set(toolNames)
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


def _microcompact(messages: list[dict[str, Any]], *, keepLast: int = 2) -> None:
    """오래된 assistant message 의 reasoning content 를 None 으로 (in-place).

    tool_calls 구조는 보존 — provider 들이 tool result 매칭에 필요. 마지막 keep_last 개의
    assistant message 는 reasoning 유지 (직전 추론 흐름 단절 방지).

    회귀 가드: graph 노드 추가 아님. messages 배열 트리밍만.
    memory/feedback_no_graph_regression.md 6 패턴과 무관.
    """
    ai_indices = [i for i, msg in enumerate(messages) if isinstance(msg, dict) and msg.get("role") == "assistant"]
    if len(ai_indices) <= keepLast:
        return
    for idx in ai_indices[:-keepLast]:
        msg = messages[idx]
        if msg.get("tool_calls") and msg.get("content"):
            msg["content"] = None


__all__ = ["runAgent"]
