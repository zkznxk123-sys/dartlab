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
    category: str = "finance",
) -> Generator[str | AnalysisEvent, None, None]:
    """Tool calling 루프.

    Args:
        category: "meta" / "finance" / "out_of_scope"
            - finance: tool 최소 1회 필수. 첫 라운드에 tool 0회면 자동 재질문.
            - meta / out_of_scope: tool 호출 자유 (0회 허용).

    제너레이터 출력:
        - AnalysisEvent("tool_call", {...})
        - AnalysisEvent("tool_result", {...})
        - str: 최종 LLM 답변 텍스트 (자유 청크)

    종료 조건:
        1. LLM 이 tool_calls 없이 답변을 내면 yield 후 종료 (FINANCE 는 첫 라운드 재질문 1회 뒤)
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
    retriggered = False  # FINANCE 가드 1회 제한

    for roundIdx in range(maxRounds):
        resp: ToolResponse | None = None
        streamedText = False

        # category → tool_choice 매핑 (첫 라운드만 강제, 이후 auto)
        tool_choice = _resolveToolChoice(category, roundIdx)

        try:
            # stream_with_tools: text delta → str 실시간 yield, 라운드 종료 → ToolResponse
            try:
                stream = llm.stream_with_tools(messages, tools, tool_choice=tool_choice)
            except TypeError:
                # tool_choice 미지원 provider — 인자 없이 재시도
                stream = llm.stream_with_tools(messages, tools)
            for item in stream:
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
                {
                    "error": f"provider '{getattr(llm.config, 'provider', '?')}' stream_with_tools 가 ToolResponse 미반환"
                },
            )
            return

        # assistant 메시지 기록 (tool_calls 포함)
        if resp.tool_calls:
            messages.append(llm.format_assistant_tool_calls(resp.answer, resp.tool_calls))
        elif resp.answer:
            messages.append({"role": "assistant", "content": resp.answer})

        # 종료: tool_calls 없음 → 최종 답변
        if not resp.tool_calls:
            # FINANCE 범주 + 첫 라운드 + tool 0회 → dartlab 정체성 훼손 → 1회 재질문
            if category == "finance" and roundIdx == 0 and not retriggered:
                retriggered = True
                yield AnalysisEvent(
                    "error",
                    {
                        "error": "[VIOLATION] 금융 분석 질문인데 dartlab tool 경유 없이 답변 시도 — 재호출 강제.",
                        "action": "tool_zero_retrigger",
                    },
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[시스템 알림] 위 답변은 dartlab 엔진을 경유하지 않아 무효입니다. "
                            "일반 ChatGPT 답변으로는 받아들일 수 없습니다.\n\n"
                            "반드시 다음 도구 중 적절한 것을 최소 1회 이상 호출한 뒤 "
                            "실측 수치 + 근거와 함께 재답변하세요:\n"
                            "- 기업 분석: analysis / credit / show / gather\n"
                            "- 매크로/시황: macro / gather(axis='macro')\n"
                            "- 시장 비교: scan / searchCompany\n"
                            "- 공시: search / gather(axis='news')\n"
                            "- 경험: pastInsight / sectorInsights"
                        ),
                    }
                )
                continue  # 다음 라운드로
            # META/OUT_OF_SCOPE 이거나 이미 재질문 1회 한 뒤 → 그대로 종료
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


def _resolveToolChoice(category: str, roundIdx: int) -> str | None:
    """category + round → tool_choice 매핑.

    - finance 첫 라운드: "any" (tool 호출 강제) — API 레벨 방어선
    - out_of_scope: "none" (tool 호출 금지)
    - meta / 나머지: None/"auto" (자율)
    """
    if category == "finance" and roundIdx == 0:
        return "any"
    if category == "out_of_scope":
        return "none"
    return None


def _hashArgs(args: dict) -> str:
    """arguments dict → 해시용 안정적 문자열."""
    import json

    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(sorted(args.items())) if args else ""
