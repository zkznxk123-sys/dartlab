"""LLM tool calling 루프 — python exec 루프 대체.

Claude Code 방식: LLM 이 JSON tool call 생성 → 런타임이 실행 → 결과를 messages 에 append → 재호출.
스키마가 enum 을 강제하므로 컬럼명/axis 추측 오류가 구조적으로 불가능.
"""

from __future__ import annotations

import logging
import traceback
from typing import Any, Generator

from dartlab.ai.runtime.events import AnalysisEvent
from dartlab.ai.runtime.progressCapture import runToolWithProgress
from dartlab.ai.runtime.quality import evaluateFinalAnswer
from dartlab.ai.tools import buildTools, executeTool, selectToolsForQuestion, toolsToOpenAiSchemas
from dartlab.ai.tools.serialize import serializeForLlm, serializeForUi
from dartlab.core.env import AuthKeyMissing

log = logging.getLogger("dartlab.ai.toolLoop")

_MAX_ROUNDS_DEFAULT = 10
_MAX_REPEAT_SAME_CALL = 2  # 동일 (name, arguments) 반복 시 강제 stop
_MAX_PARALLEL_TOOLS = 4  # 한 라운드 최대 tool 호출 수


def streamWithTools(
    llm: Any,
    messages: list[dict],
    *,
    maxRounds: int = _MAX_ROUNDS_DEFAULT,
    category: str = "finance",
    question: str | None = None,
    intent: str | None = None,
    hasCompany: bool = False,
    stockCode: str | None = None,
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

    allTools = buildTools()
    toolList = selectToolsForQuestion(
        allTools,
        question=question,
        category=category,
        intent=intent,
        hasCompany=hasCompany,
        stockCode=stockCode,
    )
    tools = toolsToOpenAiSchemas(toolList)

    from dartlab.ai.types import ToolResponse

    seenCalls: dict[str, int] = {}
    retriggered = False  # FINANCE 가드 1회 제한
    qualityRetried = False
    observedToolCalls: list[dict[str, Any]] = []

    for roundIdx in range(maxRounds):
        resp: ToolResponse | None = None
        roundTextParts: list[str] = []

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
                    roundTextParts.append(item)
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
            finalText = "".join(roundTextParts) or (resp.answer or "")
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
            quality = evaluateFinalAnswer(
                category=category,
                question=question,
                answer=finalText,
                toolCalls=observedToolCalls,
                stockCode=stockCode,
            )
            if not quality.passed and not qualityRetried:
                qualityRetried = True
                yield AnalysisEvent(
                    "quality_check",
                    {
                        "passed": False,
                        "issues": quality.issues,
                        "action": "rewrite_once",
                    },
                )
                autoCode = _krxPriceMoverAutoCode(question, observedToolCalls)
                if autoCode and not _hasObservedPythonExec(observedToolCalls):
                    autoArgs = {"code": autoCode}
                    observedToolCalls.append({"name": "pythonExec", "arguments": autoArgs})
                    yield AnalysisEvent(
                        "tool_call",
                        {
                            "id": "auto_krx_price_movers",
                            "name": "pythonExec",
                            "label": "코드 실행 — KRX 기간 수익률 계산",
                            "arguments": autoArgs,
                            "round": roundIdx + 1,
                        },
                    )
                    execTools = toolList if any(t.name == "pythonExec" for t in toolList) else allTools
                    try:
                        raw = executeTool(execTools, "pythonExec", autoArgs)
                        llmText = serializeForLlm(raw, name="pythonExec", arguments=autoArgs)
                        uiText = serializeForUi(raw, name="pythonExec")
                        status = "ok"
                    except Exception as exc:  # noqa: BLE001 - 자동 보강 실패도 audit 에 남기고 재작성으로 진행
                        llmText = f"[tool error] {type(exc).__name__}: {exc}"
                        uiText = llmText
                        status = "error"
                    yield AnalysisEvent(
                        "tool_result",
                        {
                            "id": "auto_krx_price_movers",
                            "name": "pythonExec",
                            "label": "코드 실행 — KRX 기간 수익률 계산",
                            "summary": None,
                            "result": uiText,
                            "status": status,
                            "round": roundIdx + 1,
                        },
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "[시스템 추가 계산 결과]\n"
                                "아래는 전체 KRX DataFrame 기준 기간 수익률 계산 결과입니다. "
                                "최종 답변은 이 계산 결과를 근거로 작성하세요.\n\n"
                                f"{llmText}"
                            ),
                        }
                    )
                messages.append({"role": "user", "content": quality.repairPrompt})
                continue
            if not quality.passed:
                yield AnalysisEvent(
                    "quality_check",
                    {
                        "passed": False,
                        "issues": quality.issues,
                        "action": "record_violation",
                    },
                )
            elif category == "finance":
                yield AnalysisEvent("quality_check", {"passed": True, "issues": []})
            # META/OUT_OF_SCOPE 이거나 이미 재질문 1회 한 뒤 → 그대로 종료
            if finalText:
                yield finalText
            return

        if len(resp.tool_calls) > _MAX_PARALLEL_TOOLS:
            resp.tool_calls = resp.tool_calls[:_MAX_PARALLEL_TOOLS]

        # tool 실행
        for tc in resp.tool_calls:
            callKey = f"{tc.name}:{_hashArgs(tc.arguments)}"
            seenCalls[callKey] = seenCalls.get(callKey, 0) + 1
            label = _toolLabel(tc.name, tc.arguments)
            observedToolCalls.append({"name": tc.name, "arguments": dict(tc.arguments or {})})

            yield AnalysisEvent(
                "tool_call",
                {
                    "id": tc.id,
                    "name": tc.name,
                    "label": label,
                    "arguments": tc.arguments,
                    "round": roundIdx + 1,
                },
            )

            raw: Any = None
            toolExc: BaseException | None = None
            for kind, payload in runToolWithProgress(executeTool, toolList, tc.name, tc.arguments):
                if kind == "progress":
                    yield AnalysisEvent(
                        "tool_progress",
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "line": payload,
                            "round": roundIdx + 1,
                        },
                    )
                elif kind == "done":
                    raw = payload
                elif kind == "err":
                    toolExc = payload

            if toolExc is None:
                llmText = serializeForLlm(raw, name=tc.name, arguments=tc.arguments)
                uiText = serializeForUi(raw, name=tc.name)
                status = "ok"
            elif isinstance(toolExc, AuthKeyMissing):
                # except AuthKeyMissing — runToolWithProgress 가 예외를 payload 로 전달하므로
                # try/except 블록 대신 isinstance 분기로 의미 동일하게 처리.
                # 친절 메시지 (발급 URL + .env 설정법) 이 예외 본문에 이미 포함 — 스택트레이스 불필요.
                # AI 는 이 메시지를 응답에 그대로 포함해 사용자에게 키 설정 방법을 안내한다.
                llmText = f"[API 키 필요 — 사용자에게 아래 안내를 그대로 전달하세요]\n{toolExc}"
                uiText = llmText
                status = "auth_required"
                raw = None
                log.info("tool %s: API key missing (%s)", tc.name, toolExc.envKey)
            else:
                tbText = "".join(traceback.format_exception(type(toolExc), toolExc, toolExc.__traceback__, limit=3))
                llmText = f"[tool error] {type(toolExc).__name__}: {toolExc}\n{tbText}"
                uiText = llmText
                status = "error"
                raw = None
                log.warning("tool %s failed: %s", tc.name, toolExc)

            yield AnalysisEvent(
                "tool_result",
                {
                    "id": tc.id,
                    "name": tc.name,
                    "label": label,
                    "summary": _extractToolSummary(raw) if raw is not None else None,
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


_TOOL_LABELS: dict[str, str] = {
    "searchCompany": "종목 검색",
    "analysis": "재무 분석",
    "show": "원본 데이터 조회",
    "credit": "신용등급 산출",
    "scan": "전종목 비교",
    "gather": "시장 데이터 수집",
    "macro": "매크로 분석",
    "pastInsight": "과거 분석 조회",
    "sectorInsights": "업종 분석 조회",
    "search": "공시 검색",
    "pythonExec": "코드 실행",
    "story": "보고서 생성",
    "validateStory": "스토리 검증",
    "audit": "감사 분석",
    "capital": "주주환원 분석",
    "debt": "부채 구조 분석",
    "governance": "지배구조 분석",
    "industry": "산업지도 조회",
    "topdown": "탑다운 분석",
    "quant": "정량분석",
    "causalWeights": "인과 가중치",
    "diff": "변경 비교",
    "filings": "공시 목록",
    "disclosure": "공시 조회",
    "keywordTrend": "키워드 추이",
    "codeName": "종목명 변환",
}


def _toolLabel(name: str, arguments: dict) -> str:
    """tool 호출에 대한 사람 친화적 한글 레이블."""
    base = _TOOL_LABELS.get(name, name)
    target = arguments.get("stockCode") or arguments.get("keyword") or arguments.get("query") or ""
    axis = arguments.get("axis") or arguments.get("topic") or ""
    parts = [base]
    if axis:
        parts.append(str(axis))
    if target:
        parts.append(str(target))
    return " — ".join(parts)


def _extractToolSummary(raw: Any) -> str | None:
    """tool 결과에서 _summary 1줄 추출 (autoEnrich 결과)."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        summary = raw.get("_summary")
        if isinstance(summary, str) and summary:
            return summary.split("\n")[0][:200]
        # 중첩 dict 의 첫 _summary
        for v in raw.values():
            if isinstance(v, dict) and "_summary" in v:
                s = v["_summary"]
                if isinstance(s, str) and s:
                    return s.split("\n")[0][:200]
    return None


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


def _krxPriceMoverAutoCode(question: str | None, toolCalls: list[dict[str, Any]]) -> str | None:
    """KRX 가격 모멘텀 질문에서 원본 head 표본 답변을 막기 위한 자동 계산 코드."""
    q = (question or "").lower()
    if not any(word in q for word in ("주가", "가격", "종목", "price", "stock")):
        return None
    if not any(word in q for word in ("오른", "상승", "급등", "수익률", "모멘텀", "mover", "return")):
        return None

    gatherCall = None
    for call in reversed(toolCalls):
        if str(call.get("name", "")) != "gather":
            continue
        args = call.get("arguments") or call.get("args") or {}
        if isinstance(args, dict) and str(args.get("axis", "")).lower() == "krx":
            gatherCall = args
            break
    if not gatherCall:
        return None

    import json
    import re
    from datetime import date, timedelta

    startValue = gatherCall.get("start")
    endValue = gatherCall.get("end")
    if "최근" in q and not re.search(r"(19|20)\d{2}", q):
        endValue = date.today().isoformat()
        startValue = (date.today() - timedelta(days=45)).isoformat()

    start = json.dumps(startValue, ensure_ascii=False)
    end = json.dumps(endValue, ensure_ascii=False)
    market = json.dumps(gatherCall.get("market") or "KR", ensure_ascii=False)
    return (
        "import dartlab, polars as pl\n"
        f"df = dartlab.gather('krx', 'close', start={start}, end={end}, market={market})\n"
        "date_cols = sorted([c for c in df.columns if c not in ('stockCode', 'corpName')])\n"
        "if len(date_cols) < 2:\n"
        "    print('계산 불가: KRX 가격 날짜 컬럼이 2개 미만입니다.')\n"
        "else:\n"
        "    first, last = date_cols[0], date_cols[-1]\n"
        "    df = df.with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in date_cols])\n"
        "    out = (\n"
        "        df.select(['stockCode', 'corpName', first, last])\n"
        "        .filter(pl.col(first).is_not_null() & pl.col(last).is_not_null() & (pl.col(first) > 0))\n"
        "        .with_columns((((pl.col(last) / pl.col(first)) - 1) * 100).round(2).alias('returnPct'))\n"
        "        .sort('returnPct', descending=True)\n"
        "        .head(20)\n"
        "    )\n"
        "    print(f'period: {first}~{last}, universe={df.height}, metric=close_return_pct')\n"
        "    print('rank\\tstockCode\\tcorpName\\tstartClose\\tendClose\\treturnPct')\n"
        "    for idx, row in enumerate(out.to_dicts(), start=1):\n"
        "        print(f\"{idx}\\t{row['stockCode']}\\t{row['corpName']}\\t{row[first]:.0f}\\t{row[last]:.0f}\\t{row['returnPct']:.2f}\")\n"
    )


def _hasObservedPythonExec(toolCalls: list[dict[str, Any]]) -> bool:
    return any(str(call.get("name", "")) == "pythonExec" for call in toolCalls)


def _hashArgs(args: dict) -> str:
    """arguments dict → 해시용 안정적 문자열."""
    import json

    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(sorted(args.items())) if args else ""
