"""휴리스틱 흐름 — provider 가 LLM 이 아닐 때 5 패스 노드명을 발행하며 답을 합성.

BRIEF (profile + skill_search + spec_search + planEvidence) → WORK (engine_call 루프)
→ COMPOSE (휴리스틱 답안) → GATE (verifyAnswer programmatic) → HARVEST (no-op).

본 모듈은 외부 LLM 의존 없음. targets / intent 의 정적 함수 + workbench tools 만 사용.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.tools.engineCall import engineCall
from dartlab.ai.tools.generatedSpecSearch import generatedSpecSearch
from dartlab.ai.tools.skillSearch import skillSearch
from dartlab.ai.tools.types import ToolResult
from dartlab.ai.tools.verifyAnswer import verifyAnswer

from .harvest import _wireMemory
from .scratchpad import Scratchpad
from .state import WorkbenchState
from .targets import (
    _buildQuestionProfile,
    _candidateApiRefs,
    _injectStepDependency,
    _planEvidence,
    _requiredEvidence,
    _requiresExecution,
    _skillId,
    _skillRequiresTarget,
)


def streamHeuristic(question: str, *, graphNodes: tuple[str, ...], **kwargs: Any) -> Iterator[TraceEvent]:
    """휴리스틱 path — 5 패스 노드명을 발행하며 답을 합성한다.

    graphNodes 는 loop.GRAPH_NODES — circular import 회피용 인자 주입.
    """
    state = WorkbenchState(
        question=str(question or "").strip(),
        threadId=str(kwargs.get("threadId") or ""),
        messages=list(kwargs.get("history") or kwargs.get("messages") or []),
    )
    scratchpad = Scratchpad(state.runId)
    activity_count = 0

    # ── BRIEF ──
    yield _node("brief", "질문 profile + skill/capability 후보를 만듭니다.", state)
    activity_count += 1
    state.profile = _buildQuestionProfile(state.question, stockCode=kwargs.get("stockCode"))
    state.intent = str(state.profile.get("taskType") or "research")
    scratchpad.append("brief.profile", {"profile": state.profile})

    yield _toolStart(state, "skill_search", {"query": state.question, "limit": 8})
    skill_result = skillSearch(state.question, limit=8)
    state.selectedSkillRefs = skill_result.refs
    state.refs.extend(skill_result.refs)
    state.toolCalls.append({"pass": "brief", "tool": "skill_search", "ok": skill_result.ok})
    scratchpad.append("brief.skill_search", {"result": skill_result.to_dict()})
    yield _toolResult(state, "skill_search", skill_result)
    yield TraceEvent("reference", {"refs": [ref.to_dict() for ref in skill_result.refs], "query": state.question})

    yield _toolStart(state, "generated_spec_search", {"query": state.question, "limit": 10})
    spec_result = generatedSpecSearch(state.question, limit=10)
    state.apiRefs = spec_result.refs
    state.refs.extend(spec_result.refs)
    state.toolCalls.append({"pass": "brief", "tool": "generated_spec_search", "ok": spec_result.ok})
    scratchpad.append("brief.spec_search", {"result": spec_result.to_dict()})
    yield _toolResult(state, "generated_spec_search", spec_result)

    # selectedSkillRefs 의 requiredEvidence 통합 → state.requiredEvidence
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        for ev in payload.get("requiredEvidence") or []:
            if ev not in state.requiredEvidence:
                state.requiredEvidence.append(str(ev))

    state.plan = _planEvidence(state)
    scratchpad.append("brief.plan", {"plan": state.plan})
    yield TraceEvent(
        "plan",
        {
            "profile": state.profile,
            "nodes": list(graphNodes),
            "selectedSkillIds": [_skillId(ref) for ref in state.selectedSkillRefs],
            "candidateApiRefs": _candidateApiRefs(state),
            "requiredEvidence": state.requiredEvidence or _requiredEvidence(state),
        },
    )

    # ── WORK ──
    yield _node("work", "engine_call 실행 루프.", state)
    activity_count += 1
    results: list[dict[str, Any]] = []
    for index, plan in enumerate(state.plan, start=1):
        plan = _injectStepDependency(plan, results)
        yield _toolStart(state, plan["tool"], plan["args"])
        result = _executePlan(plan)
        state.toolCalls.append({"pass": "work", "tool": plan["tool"], "ok": result.ok, "summary": result.summary})
        state.refs.extend(result.refs)
        results.append({"plan": plan, "result": result})
        scratchpad.append("work.toolResult", {"tool": plan["tool"], "args": plan["args"], "result": result.to_dict()})
        yield _toolResult(state, plan["tool"], result)
        if not result.ok:
            state.failure = result.error or "tool_failed"
            break

    if not state.plan and _skillRequiresTarget(state.selectedSkillRefs) and not state.profile.get("targets"):
        state.failure = "company_not_resolved"
    elif not state.plan and _requiresExecution(state):
        state.failure = "missing_tool_plan"

    # ── COMPOSE + GATE ──
    if state.failure is None:
        yield _node("compose", "검증된 근거로 답변을 작성합니다.", state)
        activity_count += 1
        answer = _composeAnswer(state, results)
        state.answerText = answer

        yield _node("gate", "claim ↔ ref 검증.", state)
        activity_count += 1
        verify_result = verifyAnswer(answer, state.refs)
        state.verification = verify_result.data
        state.refs.extend(verify_result.refs)
        scratchpad.append("gate.verify", verify_result.to_dict())
        yield TraceEvent("verify", {"refId": "verify:answer", "result": verify_result.data})
        if not verify_result.ok:
            state.failure = ",".join(verify_result.data.get("issues") or ["verification_failed"])
    else:
        answer = _failureMessage(state.failure)
        yield _node("gate", "도구 실패로 검증을 중단합니다.", state, status="failed")
        activity_count += 1
        yield TraceEvent("verify", {"refId": "verify:answer", "result": {"ok": False, "issues": [state.failure]}})

    # ── 실패 분기 ──
    if state.failure:
        state.status = "failed"
        failure_text = _failureMessage(state.failure)
        yield _node("gate", failure_text, state, status="failed")
        yield TraceEvent(
            "unable", {"reason": state.failure, "message": failure_text, "refs": [ref.id for ref in state.refs]}
        )
        yield TraceEvent("chunk", {"text": failure_text})
        yield TraceEvent(
            "done",
            {
                "refs": [ref.to_dict() for ref in state.refs],
                "artifacts": [],
                "verification": {"ok": False, "issues": [state.failure], "refId": "verify:answer"},
                "responseMeta": {
                    "finalEvent": "unable",
                    "responseStatus": "failed",
                    "failureReason": state.failure,
                    "activityCount": activity_count,
                    "scratchpad": scratchpad.ref(),
                    "passes": list(graphNodes),
                },
            },
        )
        return

    # ── HARVEST (휴리스틱: LLM 발굴은 no-op, 메모리 wiring 은 실행) ──
    state.status = "done"
    state.answerText = answer
    _wireMemory(state)
    yield TraceEvent("answer", {"text": answer, "evidenceRefs": [ref.id for ref in state.refs]})
    for chunk in _chunks(answer):
        yield TraceEvent("chunk", {"text": chunk})
    yield TraceEvent(
        "done",
        {
            "refs": [ref.to_dict() for ref in state.refs],
            "evidence": [ref.to_dict() for ref in state.refs if ref.kind != "verifyRef"],
            "claims": list(state.claims),
            "artifacts": _harvestArtifacts(state),
            "verification": {"ok": True, "refId": "verify:answer"},
            "responseMeta": {
                "finalEvent": "answer",
                "responseStatus": "ok",
                "refCount": len(state.refs),
                "activityCount": activity_count,
                "scratchpad": scratchpad.ref(),
                "passes": list(graphNodes),
            },
        },
    )


# ── TraceEvent 헬퍼 ──


def _node(node: str, summary: str, state: WorkbenchState, *, status: str = "running") -> TraceEvent:
    return TraceEvent(
        "graph_node", {"node": node, "summary": summary, "status": status, "state": state.public(currentNode=node)}
    )


def _toolStart(state: WorkbenchState, tool: str, args: dict[str, Any]) -> TraceEvent:
    return TraceEvent(
        "tool_start",
        {
            "id": f"{state.runId}:{len(state.toolCalls) + 1}:{tool}",
            "tool": tool,
            "input": args,
            "summary": _toolSummary(tool, args),
        },
    )


def _toolResult(state: WorkbenchState, tool: str, result: ToolResult) -> TraceEvent:
    return TraceEvent(
        "tool_result",
        {
            "id": f"{state.runId}:{len(state.toolCalls)}:{tool}",
            "tool": tool,
            "status": "done" if result.ok else "error",
            "outputSummary": result.summary,
            "evidenceRefs": [ref.id for ref in result.refs],
            "artifacts": [ref.to_dict() for ref in result.refs if ref.kind == "artifactRef"],
            "error": result.error,
        },
    )


# ── 실행 / 답변 합성 ──


def _executePlan(plan: dict[str, Any]) -> ToolResult:
    if plan["tool"] == "engine_call":
        return engineCall(plan["args"].get("plan") or plan["args"])
    raise ValueError(f"unsupported workbench tool: {plan['tool']}")


def _composeAnswer(state: WorkbenchState, results: list[dict[str, Any]]) -> str:
    tool_results = [item["result"] for item in results if item["result"].ok]
    if len(tool_results) >= 2 and _allStatementResults(tool_results):
        return _composeStatementComparison(tool_results)
    for result in tool_results:
        markdown = result.data.get("markdown")
        if markdown:
            return str(markdown)
    if tool_results:
        return _composeToolSummary(tool_results)
    return _composeReferenceAnswer(state)


def _allStatementResults(results: list[ToolResult]) -> bool:
    return all(isinstance(result.data, dict) and result.data.get("summary", {}).get("statement") for result in results)


def _composeStatementComparison(results: list[ToolResult]) -> str:
    left, right = results[0].data, results[1].data
    left_label = f"{left.get('companyName')}({left.get('stockCode')})"
    right_label = f"{right.get('companyName')}({right.get('stockCode')})"
    left_summary = left.get("summary") or {}
    right_summary = right.get("summary") or {}
    period = left_summary.get("latestPeriod")
    lines = [
        f"{left_label}와 {right_label} 재무상태표를 {period} 기준으로 비교했습니다.",
        "",
        f"| 항목 | {left.get('companyName')} | {right.get('companyName')} |",
        "|---|---:|---:|",
    ]
    left_rows = {row["item"]: row for row in left_summary.get("rows") or []}
    right_rows = {row["item"]: row for row in right_summary.get("rows") or []}
    for label in [label for label in left_rows if label in right_rows][:10]:
        lines.append(f"| {label} | {left_rows[label]['formatted']} | {right_rows[label]['formatted']} |")
    ratio = _assetRatio(left_summary, right_summary)
    if ratio is not None:
        lines.extend(
            [
                "",
                "## 핵심 차이",
                f"- 자산총계는 {left.get('companyName')}가 {right.get('companyName')}의 약 {ratio:.1f}배입니다.",
            ]
        )
    lines.append("")
    lines.append("근거는 각 회사 tableRef, valueRef, dateRef로 분리해 남겼습니다.")
    return "\n".join(lines)


def _assetRatio(left: dict[str, Any], right: dict[str, Any]) -> float | None:
    def find(summary: dict[str, Any]) -> float | None:
        for row in summary.get("rows") or []:
            if row.get("snakeId") == "total_assets":
                try:
                    return float(row.get("value"))
                except (TypeError, ValueError):
                    return None
        return None

    left_value = find(left)
    right_value = find(right)
    if left_value is None or right_value in (None, 0):
        return None
    return left_value / right_value


def _composeToolSummary(results: list[ToolResult]) -> str:
    lines = ["실행 결과를 확인했습니다.", ""]
    for result in results:
        lines.append(f"- {result.summary}")
    lines.append("")
    lines.append("근거 ref를 분리해 남겼습니다.")
    return "\n".join(lines)


def _composeReferenceAnswer(state: WorkbenchState) -> str:
    skill_rows = []
    for ref in state.selectedSkillRefs[:5]:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        skill_rows.append(
            (payload.get("id") or _skillId(ref), payload.get("title") or ref.title, payload.get("purpose") or "")
        )
    api_rows = []
    for ref in state.apiRefs[:5]:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        api_rows.append((payload.get("apiRef") or ref.id.removeprefix("api:"), payload.get("summary") or ""))
    lines = ["Skill OS와 generated spec을 기준으로 가능한 실행 경로를 확인했습니다.", ""]
    if skill_rows:
        lines.append("## 관련 skill")
        for skill_id, title, purpose in skill_rows:
            lines.append(f"- {skill_id}: {title} — {purpose}")
        lines.append("")
    if api_rows:
        lines.append("## 호출 가능한 API 후보")
        for api_ref, summary in api_rows:
            lines.append(f"- {api_ref}: {summary}")
        lines.append("")
    lines.append(
        "데이터 실행이 필요한 질문은 target, 기간, 지표를 포함하면 해당 skill/capability로 실행하고 ref 검증까지 진행합니다."
    )
    return "\n".join(lines)


def _failureMessage(reason: str) -> str:
    labels = {
        "company_not_resolved": "종목을 먼저 특정해야 분석할 수 있습니다. 예: `삼성전자 재무상태표 확인`",
        "missing_tool_plan": "선택한 skill과 generated spec으로 실행 계획을 만들지 못했습니다. 관련 skill/capability를 보강해야 합니다.",
        "empty_scan": "스캔 결과가 비어 있어 후보를 만들 수 없습니다. scan 데이터 수집 상태를 먼저 확인해야 합니다.",
        "scan_growth_no_rankable_rows": "성장성 스캔은 실행됐지만 순위를 만들 핵심 지표가 부족합니다.",
    }
    return labels.get(reason, f"답변에 필요한 근거 검증을 통과하지 못했습니다: {reason}")


def _toolSummary(tool: str, args: dict[str, Any]) -> str:
    if tool == "engine_call":
        plan = args.get("plan") or args
        api_ref = plan.get("apiRef") or f"{plan.get('engine')}.{plan.get('method')}"
        target = plan.get("target") or plan.get("axis") or plan.get("path") or ""
        return f"{api_ref} {target}".strip()
    return str(args.get("query") or args.get("target") or tool)


def _harvestArtifacts(state: WorkbenchState) -> list[dict[str, Any]]:
    return [ref.to_dict() for ref in state.refs if ref.kind == "artifactRef"]


def _chunks(text: str, *, size: int = 240) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]
