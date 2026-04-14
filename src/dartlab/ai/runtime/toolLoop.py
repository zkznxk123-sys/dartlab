"""LLM tool calling 루프 — python exec 루프 대체.

Claude Code 방식: LLM 이 JSON tool call 생성 → 런타임이 실행 → 결과를 messages 에 append → 재호출.
스키마가 enum 을 강제하므로 컬럼명/axis 추측 오류가 구조적으로 불가능.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Generator

from dartlab.ai.runtime.events import AnalysisEvent
from dartlab.ai.tools import buildTools, executeTool, toolsToOpenAiSchemas
from dartlab.ai.tools.serialize import serializeForLlm, serializeForUi

log = logging.getLogger("dartlab.ai.toolLoop")

_MAX_ROUNDS_DEFAULT = 10
_MAX_REPEAT_SAME_CALL = 2  # 동일 (name, arguments) 반복 시 강제 stop


def streamWithTools(
    llm: Any,
    messages: list[dict],
    *,
    maxRounds: int = _MAX_ROUNDS_DEFAULT,
) -> Generator[str | AnalysisEvent, None, None]:
    """Tool calling 루프.

    제너레이터 출력:
        - AnalysisEvent("tool_call", {...})
        - AnalysisEvent("tool_result", {...})
        - str: 최종 LLM 답변 텍스트 (자유 청크)

    종료 조건:
        1. LLM 이 tool_calls 없이 답변을 내면 yield 후 종료
        2. maxRounds 소진
        3. 같은 tool_call 반복 → 강제 stop
    """
    if not getattr(llm, "supports_native_tools", False):
        raise RuntimeError(
            f"provider '{getattr(llm.config, 'provider', '?')}' 는 tool calling 을 지원하지 않습니다. "
            "claude / openai / gemini / groq / cerebras / mistral 중 선택하세요."
        )

    toolList = buildTools()
    tools = toolsToOpenAiSchemas(toolList)

    from dartlab.ai.types import ToolResponse

    seenCalls: dict[str, int] = {}

    for roundIdx in range(maxRounds):
        resp: ToolResponse | None = None
        streamedText = False
        try:
            # stream_with_tools: text delta → str 실시간 yield, 라운드 종료 → ToolResponse
            for item in llm.stream_with_tools(messages, tools):
                if isinstance(item, ToolResponse):
                    resp = item
                elif isinstance(item, str):
                    streamedText = True
                    yield item  # 실시간 text chunk
        except Exception as e:  # noqa: BLE001
            yield AnalysisEvent(
                "error",
                {
                    "error": f"LLM 호출 실패 (round {roundIdx + 1}): {type(e).__name__}: {e}",
                    "round": roundIdx + 1,
                },
            )
            raise

        if resp is None:
            yield AnalysisEvent(
                "error",
                {"error": f"provider '{getattr(llm.config, 'provider', '?')}' stream_with_tools 가 ToolResponse 미반환"},
            )
            return

        # assistant 메시지 기록 (tool_calls 포함)
        if resp.tool_calls:
            messages.append(llm.format_assistant_tool_calls(resp.answer, resp.tool_calls))
        elif resp.answer:
            messages.append({"role": "assistant", "content": resp.answer})

        # 종료: tool_calls 없음 → 최종 답변
        if not resp.tool_calls:
            # streamedText=True 면 이미 delta 로 흘렀음. False 면 (fallback provider) 전체 yield.
            if not streamedText and resp.answer:
                yield resp.answer
            return

        # tool 실행
        for tc in resp.tool_calls:
            callKey = f"{tc.name}:{_hashArgs(tc.arguments)}"
            seenCalls[callKey] = seenCalls.get(callKey, 0) + 1

            yield AnalysisEvent(
                "tool_call",
                {
                    "id": tc.id,
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "round": roundIdx + 1,
                },
            )

            try:
                raw = executeTool(toolList, tc.name, tc.arguments)
                llmText = serializeForLlm(raw, name=tc.name, arguments=tc.arguments)
                uiText = serializeForUi(raw, name=tc.name)
                status = "ok"
            except Exception as e:  # noqa: BLE001
                tbText = traceback.format_exc(limit=3)
                llmText = f"[tool error] {type(e).__name__}: {e}\n{tbText}"
                uiText = llmText
                status = "error"
                log.warning("tool %s failed: %s", tc.name, e)

            yield AnalysisEvent(
                "tool_result",
                {
                    "id": tc.id,
                    "name": tc.name,
                    "result": uiText,
                    "status": status,
                    "round": roundIdx + 1,
                },
            )

            messages.append(llm.format_tool_result(tc.id, llmText))

            # 동일 호출 반복 시 강제 stop (무한루프 방지)
            if seenCalls[callKey] > _MAX_REPEAT_SAME_CALL:
                yield AnalysisEvent(
                    "error",
                    {
                        "error": f"동일 tool 호출 '{tc.name}({tc.arguments})' 이(가) "
                        f"{_MAX_REPEAT_SAME_CALL + 1}회 반복되어 중단합니다.",
                        "action": "halt_loop",
                    },
                )
                if resp.answer:
                    yield resp.answer
                return

    # 라운드 소진 — 최종 일반 completion 으로 답변 생성
    yield AnalysisEvent(
        "error",
        {
            "error": f"maxRounds={maxRounds} 소진. 최종 응답으로 종료합니다.",
            "action": "max_rounds_exhausted",
        },
    )
    try:
        yield from llm.stream(messages)
    except Exception as e:  # noqa: BLE001
        yield f"\n\n[응답 생성 실패: {type(e).__name__}: {e}]"


def _hashArgs(args: dict) -> str:
    """arguments dict → 해시용 안정적 문자열."""
    import json

    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(sorted(args.items())) if args else ""
