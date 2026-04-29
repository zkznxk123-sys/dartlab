"""LLM tool calling 루프 — python exec 루프 대체.

Claude Code 방식: LLM 이 JSON tool call 생성 → 런타임이 실행 → 결과를 messages 에 append → 재호출.
스키마가 enum 을 강제하므로 컬럼명/axis 추측 오류가 구조적으로 불가능.
"""

from __future__ import annotations

import logging
import time
import traceback
from typing import Any, Generator

from dartlab.ai.runtime.artifacts import csvArtifactsForToolResult
from dartlab.ai.runtime.contract_graph import contractIdsForQuestion, preflightActionsForQuestion, toolBudgetForQuestion
from dartlab.ai.runtime.contracts import sanitizeToolArguments
from dartlab.ai.runtime.events import AnalysisEvent
from dartlab.ai.runtime.progressCapture import runToolWithProgress
from dartlab.ai.runtime.quality import evaluateFinalAnswer
from dartlab.ai.runtime.workspace import AnalysisWorkspace
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
    workspace: AnalysisWorkspace | None = None,
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
    workspace = workspace or AnalysisWorkspace(question=question)
    workspace.coverage["contractIds"] = contractIdsForQuestion(question)

    preflightQuestion = "stock return movers" if _isNormalizedPriceMoverQuestion(question) else question
    preflightCode = _krxPriceMoverAutoCode(preflightQuestion, observedToolCalls)
    if category == "finance" and preflightCode:
        preflightArgs = {"code": preflightCode}
        observedToolCalls.append({"name": "pythonExec", "arguments": preflightArgs})
        yield AnalysisEvent(
            "tool_call",
            {
                "id": "preflight_krx_price_movers",
                "name": "pythonExec",
                "label": "KRX price mover computation",
                "arguments": preflightArgs,
                "round": 0,
            },
        )
        execTools = toolList if any(t.name == "pythonExec" for t in toolList) else allTools
        toolStart = time.perf_counter()
        try:
            raw = executeTool(execTools, "pythonExec", preflightArgs)
            output = _buildSuccessfulToolOutput(
                raw,
                name="pythonExec",
                arguments=preflightArgs,
                llm=llm,
                workspace=workspace,
            )
            llmText = output["llmText"]
            uiText = output["uiText"]
            artifacts = output["artifacts"]
            for event in output["events"]:
                yield event
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            llmText = f"[tool error] {type(exc).__name__}: {exc}"
            uiText = llmText
            artifacts = []
            status = "error"
        durationMs = int((time.perf_counter() - toolStart) * 1000)
        resultSizeBytes = _resultSizeBytes(uiText)
        workspace.recordToolLatency(
            name="pythonExec",
            durationMs=durationMs,
            resultSizeBytes=resultSizeBytes,
            round=0,
        )
        yield AnalysisEvent(
            "tool_result",
            {
                "id": "preflight_krx_price_movers",
                "name": "pythonExec",
                "label": "KRX price mover computation",
                "summary": None,
                "result": uiText,
                "artifacts": artifacts,
                "status": status,
                "round": 0,
                "durationMs": durationMs,
                "resultSizeBytes": resultSizeBytes,
            },
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "[system preflight]\n"
                    "Recent price mover questions must use this computed full-universe KRX result as primary evidence.\n\n"
                    f"{llmText}"
                ),
            }
        )

    for preflightName, preflightArgs in _cashflowPreflightCalls(
        category=category,
        intent=intent,
        stockCode=stockCode,
    ):
        preflightId = f"preflight_cashflow_{preflightName}"
        observedToolCalls.append({"name": preflightName, "arguments": dict(preflightArgs)})
        yield AnalysisEvent(
            "tool_call",
            {
                "id": preflightId,
                "name": preflightName,
                "label": _toolLabel(preflightName, preflightArgs),
                "arguments": preflightArgs,
                "round": 0,
            },
        )
        toolStart = time.perf_counter()
        try:
            raw = executeTool(allTools, preflightName, preflightArgs)
            output = _buildSuccessfulToolOutput(
                raw,
                name=preflightName,
                arguments=preflightArgs,
                llm=llm,
                workspace=workspace,
            )
            llmText = output["llmText"]
            uiText = output["uiText"]
            artifacts = output["artifacts"]
            for event in output["events"]:
                yield event
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            raw = None
            llmText = f"[tool error] {type(exc).__name__}: {exc}"
            uiText = llmText
            artifacts = []
            status = "error"
        durationMs = int((time.perf_counter() - toolStart) * 1000)
        resultSizeBytes = _resultSizeBytes(uiText)
        workspace.recordToolLatency(
            name=preflightName,
            durationMs=durationMs,
            resultSizeBytes=resultSizeBytes,
            round=0,
        )
        yield AnalysisEvent(
            "tool_result",
            {
                "id": preflightId,
                "name": preflightName,
                "label": _toolLabel(preflightName, preflightArgs),
                "summary": _extractToolSummary(raw) if raw is not None else None,
                "result": uiText,
                "artifacts": artifacts,
                "status": status,
                "round": 0,
                "durationMs": durationMs,
                "resultSizeBytes": resultSizeBytes,
            },
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "[system preflight]\n"
                    "Cash-flow questions must treat this cash-flow evidence as primary. "
                    "Do not mix credit ratios and historical narrative unless their basis is disclosed.\n\n" + llmText
                ),
            }
        )

    for preflightName, preflightArgs in _comparisonPreflightCalls(
        category=category,
        intent=intent,
        question=question,
    ):
        preflightId = f"preflight_compare_{preflightArgs.get('stockCode')}_{preflightName}"
        observedToolCalls.append({"name": preflightName, "arguments": dict(preflightArgs)})
        yield AnalysisEvent(
            "tool_call",
            {
                "id": preflightId,
                "name": preflightName,
                "label": _toolLabel(preflightName, preflightArgs),
                "arguments": preflightArgs,
                "round": 0,
            },
        )
        toolStart = time.perf_counter()
        try:
            raw = executeTool(allTools, preflightName, preflightArgs)
            output = _buildSuccessfulToolOutput(
                raw,
                name=preflightName,
                arguments=preflightArgs,
                llm=llm,
                workspace=workspace,
            )
            llmText = output["llmText"]
            uiText = output["uiText"]
            artifacts = output["artifacts"]
            for event in output["events"]:
                yield event
            status = "ok"
        except Exception as exc:  # noqa: BLE001
            raw = None
            llmText = f"[tool error] {type(exc).__name__}: {exc}"
            uiText = llmText
            artifacts = []
            status = "error"
        durationMs = int((time.perf_counter() - toolStart) * 1000)
        resultSizeBytes = _resultSizeBytes(uiText)
        workspace.recordToolLatency(
            name=preflightName,
            durationMs=durationMs,
            resultSizeBytes=resultSizeBytes,
            round=0,
        )
        yield AnalysisEvent(
            "tool_result",
            {
                "id": preflightId,
                "name": preflightName,
                "label": _toolLabel(preflightName, preflightArgs),
                "summary": _extractToolSummary(raw) if raw is not None else None,
                "result": uiText,
                "artifacts": artifacts,
                "status": status,
                "round": 0,
                "durationMs": durationMs,
                "resultSizeBytes": resultSizeBytes,
            },
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "[system preflight]\n"
                    "Comparison questions must keep target coverage balanced. "
                    "Use this target evidence as one side of the comparison.\n\n" + llmText
                ),
            }
        )

    for roundIdx in range(maxRounds):
        resp: ToolResponse | None = None
        roundTextParts: list[str] = []
        roundStart = time.perf_counter()

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
        workspace.recordLlmRound(int((time.perf_counter() - roundStart) * 1000))

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
            finalText = _cleanFinalText(finalText)
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
            finalText = _appendWorkspaceLimits(finalText, workspace)
            _resetWorkspaceClaims(workspace)
            for visual in workspace.ensureRequiredVisuals(answer=finalText):
                yield AnalysisEvent("chart", {"charts": [visual.spec], "visuals": [visual.toDict()]})
            for claim in workspace.recordFinalAnswer(finalText):
                yield AnalysisEvent("claim", claim.toDict())
            quality = evaluateFinalAnswer(
                category=category,
                question=question,
                answer=finalText,
                toolCalls=observedToolCalls,
                stockCode=stockCode,
                workspace=workspace,
            )
            if not quality.passed and not qualityRetried:
                workspace.coverage["contractViolations"] = list(quality.issues)
                qualityRetried = True
                workspace.noteQualityRewrite()
                yield AnalysisEvent(
                    "quality_check",
                    {
                        "passed": False,
                        "issues": quality.issues,
                        "action": "rewrite_once",
                    },
                )
                autoQuestion = "stock return movers" if _isNormalizedPriceMoverQuestion(question) else question
                autoCode = _krxPriceMoverAutoCode(autoQuestion, observedToolCalls)
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
                    toolStart = time.perf_counter()
                    try:
                        raw = executeTool(execTools, "pythonExec", autoArgs)
                        output = _buildSuccessfulToolOutput(
                            raw,
                            name="pythonExec",
                            arguments=autoArgs,
                            llm=llm,
                            workspace=workspace,
                        )
                        llmText = output["llmText"]
                        uiText = output["uiText"]
                        artifacts = output["artifacts"]
                        for event in output["events"]:
                            yield event
                        status = "ok"
                    except Exception as exc:  # noqa: BLE001 - 자동 보강 실패도 audit 에 남기고 재작성으로 진행
                        llmText = f"[tool error] {type(exc).__name__}: {exc}"
                        uiText = llmText
                        artifacts = []
                        status = "error"
                    durationMs = int((time.perf_counter() - toolStart) * 1000)
                    resultSizeBytes = _resultSizeBytes(uiText)
                    workspace.recordToolLatency(
                        name="pythonExec",
                        durationMs=durationMs,
                        resultSizeBytes=resultSizeBytes,
                        round=roundIdx + 1,
                    )
                    yield AnalysisEvent(
                        "tool_result",
                        {
                            "id": "auto_krx_price_movers",
                            "name": "pythonExec",
                            "label": "코드 실행 — KRX 기간 수익률 계산",
                            "summary": None,
                            "result": uiText,
                            "artifacts": artifacts,
                            "status": status,
                            "round": roundIdx + 1,
                            "durationMs": durationMs,
                            "resultSizeBytes": resultSizeBytes,
                        },
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "[시스템 추가 계산 결과]\n"
                                "아래는 전체 KRX DataFrame 기준 기간 수익률 계산 결과입니다. "
                                "최근 질문에 대해 오늘 기준 최근 45일 범위로 자동 보강한 최신 계산이며, "
                                "앞서 받은 낡은 표본보다 이 결과를 우선 근거로 작성하세요.\n\n"
                                f"{llmText}"
                            ),
                        }
                    )
                fxArgs = _macroFxAutoArgs(question, observedToolCalls)
                if fxArgs:
                    observedToolCalls.append({"name": "gather", "arguments": fxArgs})
                    yield AnalysisEvent(
                        "tool_call",
                        {
                            "id": "auto_macro_fx",
                            "name": "gather",
                            "label": "시장 데이터 수집 — macro — USDKRW",
                            "arguments": fxArgs,
                            "round": roundIdx + 1,
                        },
                    )
                    execTools = toolList if any(t.name == "gather" for t in toolList) else allTools
                    toolStart = time.perf_counter()
                    try:
                        raw = executeTool(execTools, "gather", fxArgs)
                        output = _buildSuccessfulToolOutput(
                            raw,
                            name="gather",
                            arguments=fxArgs,
                            llm=llm,
                            workspace=workspace,
                        )
                        llmText = output["llmText"]
                        uiText = output["uiText"]
                        artifacts = output["artifacts"]
                        for event in output["events"]:
                            yield event
                        status = "ok"
                    except Exception as exc:  # noqa: BLE001
                        llmText = f"[tool error] {type(exc).__name__}: {exc}"
                        uiText = llmText
                        artifacts = []
                        status = "error"
                    durationMs = int((time.perf_counter() - toolStart) * 1000)
                    resultSizeBytes = _resultSizeBytes(uiText)
                    workspace.recordToolLatency(
                        name="gather",
                        durationMs=durationMs,
                        resultSizeBytes=resultSizeBytes,
                        round=roundIdx + 1,
                    )
                    yield AnalysisEvent(
                        "tool_result",
                        {
                            "id": "auto_macro_fx",
                            "name": "gather",
                            "label": "시장 데이터 수집 — macro — USDKRW",
                            "summary": None,
                            "result": uiText,
                            "artifacts": artifacts,
                            "status": status,
                            "round": roundIdx + 1,
                            "durationMs": durationMs,
                            "resultSizeBytes": resultSizeBytes,
                        },
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "[시스템 추가 환율 데이터]\n"
                                "질문에 환율이 포함됐지만 최종 답변 근거에 USD/KRW 시계열이 부족했습니다. "
                                "아래 tool_result 의 최신 기준일, 기간, 값으로 환율 판단을 보강하세요.\n\n"
                                f"{llmText}"
                            ),
                        }
                    )
                messages.append({"role": "user", "content": quality.repairPrompt})
                continue
            if not quality.passed:
                workspace.coverage["contractViolations"] = list(quality.issues)
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

        maxParallelTools = _maxParallelToolsForProvider(llm)
        if len(resp.tool_calls) > maxParallelTools:
            resp.tool_calls = resp.tool_calls[:maxParallelTools]
        for tc in resp.tool_calls:
            tc.arguments = sanitizeToolArguments(tc.name, tc.arguments)

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
            toolStart = time.perf_counter()
            bypass = _toolBudgetBypass(
                tc.name,
                tc.arguments,
                observedToolCalls=observedToolCalls[:-1],
                intent=intent,
                question=question,
            ) or _fastToolBypass(tc.name, tc.arguments)
            if bypass is not None:
                raw = bypass
            else:
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
                output = _buildSuccessfulToolOutput(
                    raw,
                    name=tc.name,
                    arguments=tc.arguments,
                    llm=llm,
                    workspace=workspace,
                )
                llmText = output["llmText"]
                uiText = output["uiText"]
                artifacts = output["artifacts"]
                for event in output["events"]:
                    yield event
                status = "ok"
            elif isinstance(toolExc, AuthKeyMissing):
                # except AuthKeyMissing — runToolWithProgress 가 예외를 payload 로 전달하므로
                # try/except 블록 대신 isinstance 분기로 의미 동일하게 처리.
                # 친절 메시지 (발급 URL + .env 설정법) 이 예외 본문에 이미 포함 — 스택트레이스 불필요.
                # AI 는 이 메시지를 응답에 그대로 포함해 사용자에게 키 설정 방법을 안내한다.
                llmText = f"[API 키 필요 — 사용자에게 아래 안내를 그대로 전달하세요]\n{toolExc}"
                uiText = llmText
                artifacts = []
                status = "auth_required"
                raw = None
                log.info("tool %s: API key missing (%s)", tc.name, toolExc.envKey)
            else:
                tbText = "".join(traceback.format_exception(type(toolExc), toolExc, toolExc.__traceback__, limit=3))
                llmText = f"[tool error] {type(toolExc).__name__}: {toolExc}\n{tbText}"
                uiText = llmText
                artifacts = []
                status = "error"
                raw = None
                log.warning("tool %s failed: %s", tc.name, toolExc)

            durationMs = int((time.perf_counter() - toolStart) * 1000)
            resultSizeBytes = _resultSizeBytes(uiText)
            workspace.recordToolLatency(
                name=tc.name,
                durationMs=durationMs,
                resultSizeBytes=resultSizeBytes,
                round=roundIdx + 1,
            )
            yield AnalysisEvent(
                "tool_result",
                {
                    "id": tc.id,
                    "name": tc.name,
                    "label": label,
                    "summary": _extractToolSummary(raw) if raw is not None else None,
                    "result": uiText,
                    "artifacts": artifacts,
                    "status": status,
                    "round": roundIdx + 1,
                    "durationMs": durationMs,
                    "resultSizeBytes": resultSizeBytes,
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
    fallbackText = _compileWorkspaceFallback(question, workspace)
    if fallbackText:
        workspace.markMaxRoundsReached()
        fallbackText = _appendWorkspaceLimits(fallbackText, workspace)
        _resetWorkspaceClaims(workspace)
        for visual in workspace.ensureRequiredVisuals(answer=fallbackText):
            yield AnalysisEvent("chart", {"charts": [visual.spec], "visuals": [visual.toDict()]})
        for claim in workspace.recordFinalAnswer(fallbackText):
            yield AnalysisEvent("claim", claim.toDict())
        quality = evaluateFinalAnswer(
            category=category,
            question=question,
            answer=fallbackText,
            toolCalls=observedToolCalls,
            stockCode=stockCode,
            workspace=workspace,
        )
        yield AnalysisEvent(
            "quality_check",
            {
                "passed": quality.passed,
                "issues": quality.issues,
                "action": "compiler_fallback",
            },
        )
        yield fallbackText
        return

    workspace.markMaxRoundsReached()
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


def _compileWorkspaceFallback(question: str | None, workspace: AnalysisWorkspace) -> str:
    evidence = list(getattr(workspace, "evidence", []) or [])
    if not evidence:
        return ""

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in evidence:
        target = str(getattr(item, "target", "") or "-")
        metric = str(getattr(item, "metric", "") or "-")
        asOf = str(getattr(item, "asOf", "") or getattr(item, "period", "") or "-")
        key = (target, metric, asOf)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "target": target,
                "metric": metric,
                "asOf": asOf,
                "value": _formatFallbackValue(getattr(item, "value", None)),
                "basis": str(getattr(item, "basis", "") or getattr(item, "sourceTool", "") or "-")[:80],
            }
        )
        if len(rows) >= 10:
            break
    if not rows:
        return ""

    questionText = question or getattr(workspace, "question", "") or "요청"
    lines = [
        f"도구 호출이 많아져 런타임이 보유한 근거 장부 기준으로 답변을 컴파일합니다. **{questionText}에 대한 판단은 아래 표의 확인된 수치 범위 안에서만 유효합니다.**",
        "",
        "| 대상 | 지표 | 기준 | 값 | 근거 |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['target']} | {row['metric']} | {row['asOf']} | {row['value']} | {row['basis']} |")
    lines.extend(
        [
            "",
            "이 표에서 읽을 포인트",
            "- 최종 답변은 이미 실행된 dartlab tool evidence만 사용했습니다.",
            "- 같은 지표가 여러 대상에 존재할 때만 비교 결론을 강하게 냅니다.",
            "- 누락된 축은 추가 단정 없이 한계로 남깁니다.",
            "",
            "판단: 현재 확보된 근거만 보면 강한 단정은 피하고, 표에 있는 공통 지표를 중심으로 제한적 판단을 내리는 것이 맞습니다.",
        ]
    )
    return "\n".join(lines)


def _cleanFinalText(text: str) -> str:
    import re

    lines = [line for line in text.splitlines() if line.strip() not in {"#", "##", "###", "####"}]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _cashflowPreflightCalls(
    *,
    category: str,
    intent: str | None,
    stockCode: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    actions = preflightActionsForQuestion(
        question="현금흐름",
        category=category,
        intent=intent,
        stockCode=stockCode,
    )
    return [(tool, args) for tool, args, contract in actions if contract.contractId == "cashflow.primary"]


def _comparisonPreflightCalls(
    *,
    category: str,
    intent: str | None,
    question: str | None,
) -> list[tuple[str, dict[str, Any]]]:
    if category != "finance" or intent != "compare" or not question:
        return []
    targets = _comparisonTargetsFromQuestion(question)
    if len(targets) < 2:
        return []
    return [("analysis", {"stockCode": code, "axis": "종합평가"}) for code in targets[:2]]


def _comparisonTargetsFromQuestion(question: str) -> list[str]:
    import re

    try:
        from dartlab.core.resolve import collect_candidates, resolve_alias, strip_particles
    except Exception:
        return []

    targets: list[str] = []
    for token in re.findall(r"[0-9A-Za-z가-힣]+", question):
        if len(token) < 2:
            continue
        keyword = resolve_alias(token) or resolve_alias(strip_particles(token)) or strip_particles(token)
        try:
            candidates = collect_candidates(keyword, strict=True)
        except Exception:
            continue
        if not candidates:
            continue
        code = str(candidates[0].get("stockCode") or candidates[0].get("code") or "").strip()
        if code and code not in targets:
            targets.append(code)
        if len(targets) >= 2:
            break
    return targets


def _formatFallbackValue(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, (int, bool)):
        return str(value)
    text = str(value).replace("\n", " ").strip()
    return text[:80] if text else "-"


def _appendWorkspaceLimits(text: str, workspace: AnalysisWorkspace) -> str:
    limits = _freshnessLimitSummary(workspace)
    if not limits:
        return text
    disclosure_terms = (
        "가용 데이터",
        "데이터 한계",
        "최신 데이터",
        "기준일",
        "snapshot",
        "available through",
        "available data",
        "freshness",
        "한계",
    )
    if any(term in text for term in disclosure_terms):
        return text
    limitText = "; ".join(str(limit) for limit in limits[:3])
    return (
        text.rstrip()
        + "\n\n데이터 한계: "
        + limitText
        + ". 현재 상황을 단정한 것이 아니라 가용 데이터 기준의 판단입니다."
    )


def _freshnessLimitSummary(workspaceOrLimits: Any) -> list[str]:
    import re

    freshness = getattr(workspaceOrLimits, "freshness", None)
    if isinstance(freshness, dict):
        summarized: list[str] = []
        for metric, data in freshness.items():
            if not isinstance(data, dict) or not data.get("staleDaily"):
                continue
            asOf = str(data.get("latestAsOf") or "").strip()
            if asOf:
                summarized.append(f"freshness: {metric} available through {asOf}")
        if summarized:
            return summarized

    limits = workspaceOrLimits if isinstance(workspaceOrLimits, list) else getattr(workspaceOrLimits, "limits", [])
    latestByMetric: dict[str, tuple[str, str]] = {}
    fallback: list[str] = []
    for raw in limits:
        limit = str(raw)
        if not limit.startswith("freshness:"):
            continue
        match = re.search(r"freshness:\s*([^ ]+).*?available through\s+(\d{4}-\d{2}-\d{2})", limit)
        if not match:
            fallback.append(limit)
            continue
        metric = match.group(1)
        asOf = match.group(2)
        previous = latestByMetric.get(metric)
        if previous is None or asOf > previous[0]:
            latestByMetric[metric] = (asOf, limit)
    summarized = [item[1] for item in latestByMetric.values()]
    return summarized or fallback


def _fastToolBypass(name: str, arguments: dict[str, Any] | None) -> dict[str, Any] | None:
    args = arguments or {}
    stockCode = str(args.get("stockCode") or "").strip()
    if name == "analysis" and stockCode and not stockCode.isdigit():
        return {
            "_summary": (
                "analysis tool skipped by runtime budget for a non-KR ticker; "
                "use credit, quant, show, and other available evidence instead."
            ),
            "stockCode": stockCode,
            "basis": "runtime_tool_budget",
            "limitations": ["analysis is optimized for domestic stock codes in this runtime path"],
        }
    if name == "credit" and stockCode and not stockCode.isdigit():
        return {
            "_summary": (
                "credit tool skipped by runtime latency budget for a non-KR ticker; "
                "use quant, show, macro, and disclosed limitations instead."
            ),
            "stockCode": stockCode,
            "basis": "runtime_tool_budget",
            "limitations": ["foreign ticker credit detail can exceed the audit latency budget"],
        }
    if name == "quant" and stockCode and not stockCode.isdigit():
        return {
            "_summary": (
                "quant tool skipped by runtime latency budget for a non-KR ticker; "
                "use show, macro, and disclosed limitations instead."
            ),
            "stockCode": stockCode,
            "basis": "runtime_tool_budget",
            "limitations": ["foreign ticker quant detail can exceed the audit latency budget"],
        }
    return None


def _toolBudgetBypass(
    name: str,
    arguments: dict[str, Any] | None,
    *,
    observedToolCalls: list[dict[str, Any]],
    intent: str | None,
    question: str | None = None,
) -> dict[str, Any] | None:
    budget = toolBudgetForQuestion(question, intent)
    if intent != "compare" or name not in {"analysis", "quant", "credit"}:
        return None
    args = arguments or {}
    stockCode = str(args.get("stockCode") or "").strip()
    if not stockCode:
        return None
    skipTools = set(str(v) for v in budget.get("skipTools") or ())
    if name in skipTools:
        return {
            "_summary": (
                f"{name} skipped by comparison tool budget for {stockCode}; "
                "comparison uses balanced fundamental evidence instead."
            ),
            "stockCode": stockCode,
            "basis": "runtime_tool_budget",
            "limitations": ["comparison runtime skips quant to avoid unbalanced slow axes"],
        }
    previous = 0
    for call in observedToolCalls:
        if str(call.get("name") or "") != name:
            continue
        callArgs = call.get("arguments") or call.get("args") or {}
        if isinstance(callArgs, dict) and str(callArgs.get("stockCode") or "").strip() == stockCode:
            previous += 1
    maxCalls = int(budget.get("maxHeavyCallsPerTargetTool") or 1)
    if previous < maxCalls:
        return None
    return {
        "_summary": (
            f"{name} skipped by comparison tool budget after one call for {stockCode}; "
            "keep target coverage balanced instead of adding more axes."
        ),
        "stockCode": stockCode,
        "basis": "runtime_tool_budget",
        "limitations": ["comparison budget allows one heavy evidence call per target/tool"],
    }


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
    if any(word in q for word in ("주가", "가격", "종목", "stock", "price")) and any(
        word in q for word in ("오른", "상승", "수익률", "랭킹", "순위", "mover", "return")
    ):
        q += " price return"
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
    import json
    import re
    from datetime import date, timedelta

    startValue = gatherCall.get("start") if gatherCall else None
    endValue = gatherCall.get("end") if gatherCall else None
    if "최근" in q and not re.search(r"(19|20)\d{2}", q):
        endValue = date.today().isoformat()
        startValue = (date.today() - timedelta(days=45)).isoformat()

    if startValue is None:
        startValue = (date.today() - timedelta(days=45)).isoformat()
    if endValue is None:
        endValue = date.today().isoformat()

    start = json.dumps(startValue, ensure_ascii=False)
    end = json.dumps(endValue, ensure_ascii=False)
    market = json.dumps((gatherCall or {}).get("market") or "KR", ensure_ascii=False)
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


def _isNormalizedPriceMoverQuestion(question: str | None) -> bool:
    q = (question or "").lower()
    hasStock = any(word in q for word in ("주가", "가격", "종목", "stock", "price"))
    hasMove = any(word in q for word in ("오른", "상승", "수익률", "랭킹", "순위", "mover", "return"))
    return hasStock and hasMove


def _macroFxAutoArgs(question: str | None, toolCalls: list[dict[str, Any]]) -> dict[str, Any] | None:
    q = (question or "").lower()
    if not any(word in q for word in ("환율", "원달러", "원/달러", "usdkrw", "krwusd", "fx", "exchange")):
        return None

    try:
        from dartlab.gather.ecos.catalog import resolveId
    except Exception:  # pragma: no cover - catalog import failure is non-critical here

        def resolveId(value: str) -> str:
            return value

    for call in toolCalls:
        if str(call.get("name", "")) != "gather":
            continue
        args = call.get("arguments") or call.get("args") or {}
        if not isinstance(args, dict) or str(args.get("axis") or "").lower() != "macro":
            continue
        target = str(args.get("target") or "")
        if resolveId(target) == "USDKRW":
            return None

    from datetime import date, timedelta

    today = date.today()
    return {
        "axis": "macro",
        "target": "USDKRW",
        "start": (today - timedelta(days=120)).isoformat(),
        "end": today.isoformat(),
        "market": "KR",
    }


def _capToolResultForProvider(text: str, *, llm: Any) -> str:
    """Provider별 backend 한도를 피하기 위해 LLM용 tool_result만 압축한다."""
    provider = str(getattr(getattr(llm, "config", None), "provider", "") or "")
    limit = 1800 if provider == "oauth-codex" else 8000
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... (+{len(text) - limit} chars 잘림; 필요한 값은 추가 tool 호출로 조회)"


def _buildSuccessfulToolOutput(
    raw: Any,
    *,
    name: str,
    arguments: dict[str, Any],
    llm: Any,
    workspace: AnalysisWorkspace | None,
) -> dict[str, Any]:
    """Build LLM/UI text, CSV artifacts, and workspace events for an ok tool result."""
    cleanRaw = raw
    specs: list[dict[str, Any]] = []
    if isinstance(raw, str):
        try:
            from dartlab.viz.extract import extract_viz_specs

            cleaned, specs = extract_viz_specs(raw)
            cleanRaw = cleaned if specs else raw
        except Exception:  # noqa: BLE001 - viz extraction must not break tool results
            cleanRaw = raw
            specs = []

    llmText = _capToolResultForProvider(serializeForLlm(cleanRaw, name=name, arguments=arguments), llm=llm)
    uiText = serializeForUi(cleanRaw, name=name)
    artifacts = csvArtifactsForToolResult(cleanRaw, name=name, arguments=arguments)
    events: list[AnalysisEvent] = []

    if workspace is not None:
        evidenceItems = workspace.recordToolResult(
            sourceTool=name,
            arguments=arguments,
            result=cleanRaw,
            artifacts=artifacts,
        )
        for item in evidenceItems:
            events.append(AnalysisEvent("evidence", item.toDict()))
        if not specs and _shouldAutoVisual(arguments=arguments, evidenceItems=evidenceItems):
            specs = [_autoChartSpec(name=name, arguments=arguments, evidenceItems=evidenceItems)]
        if specs:
            visuals = []
            for spec in specs:
                visual = workspace.recordVisualSpec(
                    spec,
                    purpose=_visualPurpose(name=name, arguments=arguments),
                    evidenceIds=[item.id for item in evidenceItems] or None,
                )
                visuals.append(visual.toDict())
            events.append(AnalysisEvent("chart", {"charts": specs, "visuals": visuals}))

    return {"llmText": llmText, "uiText": uiText, "artifacts": artifacts, "events": events}


def _visualPurpose(*, name: str, arguments: dict[str, Any]) -> str:
    axis = arguments.get("axis") or arguments.get("target") or arguments.get("topic")
    if axis:
        return f"{name}:{axis}"
    return name


def _shouldAutoVisual(*, arguments: dict[str, Any], evidenceItems: list[Any]) -> bool:
    if len(evidenceItems) < 2:
        return False
    q = " ".join(str(arguments.get(k) or "") for k in ("axis", "target", "topic"))
    if any(word in q.lower() for word in ("krx", "close", "rank", "growth", "price", "macro")):
        return True
    numeric = [item for item in evidenceItems if _numericValue(getattr(item, "value", None)) is not None]
    return len(numeric) >= 2


def _autoChartSpec(*, name: str, arguments: dict[str, Any], evidenceItems: list[Any]) -> dict[str, Any]:
    rows = [
        item
        for item in evidenceItems
        if getattr(item, "target", None) and _numericValue(getattr(item, "value", None)) is not None
    ]
    rows = rows[:20]
    metric = next((str(getattr(item, "metric", "")) for item in rows if getattr(item, "metric", None)), "value")
    return {
        "vizType": "chart",
        "chartType": "bar",
        "title": f"{name} {metric}",
        "categories": [str(getattr(item, "target", "")) for item in rows],
        "series": [{"name": metric, "data": [_numericValue(getattr(item, "value", None)) for item in rows]}],
        "options": {"unit": getattr(rows[0], "unit", None) if rows else None},
        "meta": {
            "source": name,
            "axis": arguments.get("axis"),
            "target": arguments.get("target"),
            "generated": "runtime",
        },
    }


def _numericValue(value: Any) -> float | int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        raw = value.replace(",", "").replace("%", "").strip()
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _resultSizeBytes(value: Any) -> int:
    try:
        return len(str(value).encode("utf-8", errors="replace"))
    except Exception:  # noqa: BLE001
        return 0


def _resetWorkspaceClaims(workspace: AnalysisWorkspace) -> None:
    workspace.claims.clear()
    workspace._claimRecorded = False  # noqa: SLF001 - request-local retry reset


def _maxParallelToolsForProvider(llm: Any) -> int:
    provider = str(getattr(getattr(llm, "config", None), "provider", "") or "")
    if provider == "oauth-codex":
        return 2
    return _MAX_PARALLEL_TOOLS


def _hashArgs(args: dict) -> str:
    """arguments dict → 해시용 안정적 문자열."""
    import json

    try:
        return json.dumps(args, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(sorted(args.items())) if args else ""
