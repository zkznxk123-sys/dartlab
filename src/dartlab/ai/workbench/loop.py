"""Ask Workbench loop backed by Skill OS and generated capabilities."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import Ref, TraceEvent
from dartlab.ai.tools.engineCall import engineCall
from dartlab.ai.tools.generatedSpecSearch import generatedSpecSearch
from dartlab.ai.tools.skillSearch import skillSearch
from dartlab.ai.tools.types import ToolResult
from dartlab.ai.tools.verifyAnswer import verifyAnswer

from .scratchpad import Scratchpad
from .state import WorkbenchState

GRAPH_NODES: tuple[str, ...] = (
    "routeIntent",
    "selectSkill",
    "searchCapability",
    "planEvidence",
    "executeTool",
    "observeResult",
    "verifyClaims",
    "composeAnswer",
    "repairOrFail",
)

_COMPANY_SPLIT_RE = re.compile(r"\s*(?:,|/|vs\.?|VS\.?|랑|하고|와|과)\s*")
_STOCK_CODE_RE = re.compile(r"\b\d{6}\b")
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")
_SHOW_TOPIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("BS", ("BS", "balance sheet", "재무상태표", "재무제표", "자산", "부채", "자본")),
    ("IS", ("IS", "income statement", "손익계산서", "손익", "이익", "매출")),
    ("CF", ("CF", "cash flow", "현금흐름표", "현금흐름", "FCF", "free cash flow")),
)
_ACTION_WORDS = (
    "확인",
    "비교",
    "분석",
    "설명",
    "계산",
    "알려줘",
    "해줘",
    "봐줘",
    "찾아줘",
    "재무제표",
    "재무상태표",
    "손익계산서",
    "현금흐름표",
    "자산",
    "부채",
    "자본",
)
_EVIDENCE_EXECUTION_NAMES = {
    "execution",
    "executionRef",
    "table",
    "tableRef",
    "value",
    "valueRef",
    "date",
    "dateRef",
    "dataset",
    "datasetRef",
    "datasetAsOf",
    "universe",
    "filter",
    "formula",
}
_NON_EXECUTABLE_API_REFS = {"ask", "Company.ask", "ChartResult"}


class WorkbenchLoop:
    """Production ask loop.

    The loop does not route by question-specific answer templates.  It first
    searches root Skill OS, then generated capabilities/docstrings, then builds
    executable tool plans from those refs.
    """

    nodes = GRAPH_NODES

    def stream(self, question: str, **kwargs: Any) -> Iterator[TraceEvent]:
        state = WorkbenchState(
            question=str(question or "").strip(),
            threadId=str(kwargs.get("threadId") or ""),
            messages=list(kwargs.get("history") or kwargs.get("messages") or []),
        )
        scratchpad = Scratchpad(state.runId)
        activity_count = 0

        state.profile = _buildQuestionProfile(state.question, stockCode=kwargs.get("stockCode"))
        state.intent = str(state.profile.get("taskType") or "research")
        yield self._node("routeIntent", "질문 profile을 만들었습니다.", state)
        activity_count += 1
        scratchpad.append("routeIntent", {"profile": state.profile})

        yield self._node("selectSkill", "Skill OS에서 실행 절차를 찾습니다.", state)
        activity_count += 1
        yield self._tool_start(state, "skill_search", {"query": state.question, "limit": 8})
        skill_result = skillSearch(state.question, limit=8)
        state.selectedSkillRefs = skill_result.refs
        state.refs.extend(skill_result.refs)
        state.toolCalls.append({"tool": "skill_search", "ok": skill_result.ok})
        scratchpad.append("toolResult", {"tool": "skill_search", "result": skill_result.to_dict()})
        yield self._tool_result(state, "skill_search", skill_result)
        yield TraceEvent("reference", {"refs": [ref.to_dict() for ref in skill_result.refs], "query": state.question})

        yield self._node("searchCapability", "generated spec/docstring에서 호출 가능한 API를 찾습니다.", state)
        activity_count += 1
        yield self._tool_start(state, "generated_spec_search", {"query": state.question, "limit": 10})
        spec_result = generatedSpecSearch(state.question, limit=10)
        state.apiRefs = spec_result.refs
        state.refs.extend(spec_result.refs)
        state.toolCalls.append({"tool": "generated_spec_search", "ok": spec_result.ok})
        scratchpad.append("toolResult", {"tool": "generated_spec_search", "result": spec_result.to_dict()})
        yield self._tool_result(state, "generated_spec_search", spec_result)

        yield self._node("planEvidence", "skill/capability refs로 실행 계획을 만듭니다.", state)
        activity_count += 1
        state.plan = _planEvidence(state)
        scratchpad.append("planEvidence", {"plan": state.plan})
        yield TraceEvent(
            "plan",
            {
                "profile": state.profile,
                "nodes": list(self.nodes),
                "selectedSkillIds": [_skillId(ref) for ref in state.selectedSkillRefs],
                "candidateApiRefs": _candidateApiRefs(state),
                "requiredEvidence": _requiredEvidence(state),
            },
        )

        results: list[dict[str, Any]] = []
        for index, plan in enumerate(state.plan, start=1):
            yield self._node("executeTool", f"{plan['tool']} 실행 {index}/{len(state.plan)}", state)
            activity_count += 1
            yield self._tool_start(state, plan["tool"], plan["args"])
            result = _executePlan(plan)
            state.toolCalls.append({"tool": plan["tool"], "ok": result.ok, "summary": result.summary})
            state.refs.extend(result.refs)
            results.append({"plan": plan, "result": result})
            scratchpad.append("toolResult", {"tool": plan["tool"], "args": plan["args"], "result": result.to_dict()})
            yield self._tool_result(state, plan["tool"], result)
            yield self._node("observeResult", result.summary, state, status="done" if result.ok else "failed")
            activity_count += 1
            if not result.ok:
                state.failure = result.error or "tool_failed"
                break

        if not state.plan and _skillRequiresTarget(state.selectedSkillRefs) and not state.profile.get("targets"):
            state.failure = "company_not_resolved"
        elif not state.plan and _requiresExecution(state):
            state.failure = "missing_tool_plan"

        if state.failure is None:
            answer = _composeAnswer(state, results)
            verify_result = verifyAnswer(answer, state.refs)
            state.verification = verify_result.data
            state.refs.extend(verify_result.refs)
            scratchpad.append("verifyClaims", verify_result.to_dict())
            yield self._node("verifyClaims", "숫자/날짜/근거를 검증합니다.", state)
            activity_count += 1
            yield TraceEvent("verify", {"refId": "verify:answer", "result": verify_result.data})
            if not verify_result.ok:
                state.failure = ",".join(verify_result.data.get("issues") or ["verification_failed"])
        else:
            answer = _failureMessage(state.failure)
            yield self._node("verifyClaims", "도구 실패로 검증을 중단합니다.", state, status="failed")
            activity_count += 1
            yield TraceEvent("verify", {"refId": "verify:answer", "result": {"ok": False, "issues": [state.failure]}})

        if state.failure:
            state.status = "failed"
            failure_text = _failureMessage(state.failure)
            yield self._node("repairOrFail", failure_text, state, status="failed")
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
                    },
                },
            )
            return

        state.status = "done"
        yield self._node("composeAnswer", "검증된 근거로 답변을 작성합니다.", state, status="done")
        activity_count += 1
        yield TraceEvent("answer", {"text": answer, "evidenceRefs": [ref.id for ref in state.refs]})
        for chunk in _chunks(answer):
            yield TraceEvent("chunk", {"text": chunk})
        yield TraceEvent(
            "done",
            {
                "refs": [ref.to_dict() for ref in state.refs],
                "artifacts": [],
                "verification": {"ok": True, "refId": "verify:answer"},
                "responseMeta": {
                    "finalEvent": "answer",
                    "responseStatus": "ok",
                    "refCount": len(state.refs),
                    "activityCount": activity_count,
                    "scratchpad": scratchpad.ref(),
                },
            },
        )

    def _node(self, node: str, summary: str, state: WorkbenchState, *, status: str = "running") -> TraceEvent:
        return TraceEvent(
            "graph_node", {"node": node, "summary": summary, "status": status, "state": state.public(currentNode=node)}
        )

    def _tool_start(self, state: WorkbenchState, tool: str, args: dict[str, Any]) -> TraceEvent:
        return TraceEvent(
            "tool_start",
            {
                "id": f"{state.runId}:{len(state.toolCalls) + 1}:{tool}",
                "tool": tool,
                "input": args,
                "summary": _toolSummary(tool, args),
            },
        )

    def _tool_result(self, state: WorkbenchState, tool: str, result: ToolResult) -> TraceEvent:
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


def _buildQuestionProfile(question: str, *, stockCode: Any = None) -> dict[str, Any]:
    targets = _extractTargets(question, stockCode=stockCode)
    comparison = len(targets) >= 2
    task_type = "companyResearch" if targets else "research"
    return {
        "taskType": task_type,
        "targets": targets,
        "comparison": comparison,
        "showTopic": _inferShowTopic(question),
    }


def _extractTargets(question: str, *, stockCode: Any = None) -> list[str]:
    if stockCode:
        return [str(stockCode)]
    text = str(question or "").strip()
    stock_codes = _STOCK_CODE_RE.findall(text)
    if stock_codes:
        return list(dict.fromkeys(stock_codes))
    ticker_hits = [value for value in _TICKER_RE.findall(text) if value not in {"BS", "IS", "CF", "FCF"}]
    if ticker_hits:
        return list(dict.fromkeys(ticker_hits))
    parts = [part.strip() for part in _COMPANY_SPLIT_RE.split(text) if part.strip()]
    cleaned: list[str] = []
    for part in parts if len(parts) > 1 else [text]:
        value = _cleanTargetPhrase(part)
        if _looksLikeTarget(value) and value not in cleaned:
            cleaned.append(value)
    return cleaned[:3]


def _cleanTargetPhrase(value: str) -> str:
    cleaned = str(value or "")
    for word in _ACTION_WORDS:
        cleaned = cleaned.replace(word, " ")
    return " ".join(cleaned.split()).strip()


def _looksLikeTarget(value: str) -> bool:
    compact = str(value or "").strip()
    if not compact:
        return False
    if _STOCK_CODE_RE.fullmatch(compact) or _TICKER_RE.fullmatch(compact):
        return True
    if " " in compact:
        return False
    if compact in {"회사", "기업", "종목", "기능", "사용법", "질문", "분석", "비교", "확인"}:
        return False
    return 2 <= len(compact) <= 24


def _inferShowTopic(question: str) -> str:
    lowered = str(question or "").lower()
    for topic, aliases in _SHOW_TOPIC_ALIASES:
        if any(alias.lower() in lowered for alias in aliases):
            return topic
    return "BS"


def _planEvidence(state: WorkbenchState) -> list[dict[str, Any]]:
    candidates = _candidateApiRefs(state)
    targets = list(state.profile.get("targets") or [])
    plans: list[dict[str, Any]] = []

    scan_ref = _firstScanRef(candidates, state.selectedSkillRefs)
    if scan_ref is not None and not targets:
        plans.append(
            {
                "tool": "engine_call",
                "args": {"plan": {"apiRef": scan_ref, "axis": _scanAxis(scan_ref, state.selectedSkillRefs)}},
            }
        )
        return plans

    if targets:
        company_ref = _firstCompanyRef(candidates)
        if company_ref == "Company.show" or _skillRequiresTable(state.selectedSkillRefs):
            return [
                {
                    "tool": "engine_call",
                    "args": {
                        "plan": {
                            "apiRef": "Company.show",
                            "target": target,
                            "topic": state.profile.get("showTopic") or "BS",
                            "question": state.question,
                        }
                    },
                }
                for target in targets[:2]
            ]
        if company_ref:
            return [
                {
                    "tool": "engine_call",
                    "args": {
                        "plan": _companyPlan(company_ref, target, state.selectedSkillRefs, question=state.question)
                    },
                }
                for target in targets[:2]
            ]

    if _skillRequiresTarget(state.selectedSkillRefs):
        return plans

    capability_ref = _firstCapabilityRef(candidates)
    if capability_ref:
        key = _capabilityKeyFromSkills(state.selectedSkillRefs)
        plans.append({"tool": "engine_call", "args": {"plan": {"apiRef": capability_ref, "path": key}}})
    return plans


def _candidateApiRefs(state: WorkbenchState) -> list[str]:
    refs: list[str] = []
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        refs.extend(str(item) for item in payload.get("capabilityRefs") or [])
    for ref in state.apiRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        api_ref = payload.get("apiRef") or ref.id.removeprefix("api:")
        if api_ref:
            refs.append(str(api_ref))
    return [ref for ref in dict.fromkeys(refs) if _isExecutableApiRef(ref)]


def _isExecutableApiRef(api_ref: str) -> bool:
    if not api_ref or api_ref in _NON_EXECUTABLE_API_REFS:
        return False
    if api_ref.startswith("aiContract."):
        return False
    return True


def _firstScanRef(candidates: list[str], skill_refs: list[Ref]) -> str | None:
    skill_ids = [_skillId(ref) for ref in skill_refs]
    if not any(skill_id.startswith("engines.scan") for skill_id in skill_ids):
        return None
    for api_ref in candidates:
        if api_ref.startswith("scan."):
            return api_ref
    if "scan" in candidates:
        return "scan"
    return None


def _scanAxis(api_ref: str, skill_refs: list[Ref]) -> str:
    if api_ref.startswith("scan."):
        return api_ref.split(".", 1)[1]
    for ref in skill_refs:
        skill_id = _skillId(ref)
        if skill_id.startswith("engines.scan."):
            return skill_id.rsplit(".", 1)[1]
    return "screen"


def _firstCompanyRef(candidates: list[str]) -> str | None:
    if "Company.show" in candidates:
        return "Company.show"
    for api_ref in candidates:
        if api_ref.startswith("Company.") and api_ref not in {"Company", "Company.ask"}:
            return api_ref
    return None


def _firstCapabilityRef(candidates: list[str]) -> str | None:
    for api_ref in candidates:
        if api_ref in {"capabilities", "dartlab.capabilities"}:
            return api_ref
    return None


def _skillRequiresTable(skill_refs: list[Ref]) -> bool:
    for ref in skill_refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required = {str(item) for item in payload.get("requiredEvidence") or []}
        if required & {"table", "tableRef", "valueRef", "dateRef"}:
            return True
    return False


def _skillRequiresTarget(skill_refs: list[Ref]) -> bool:
    for ref in skill_refs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required = {str(item) for item in payload.get("requiredEvidence") or []}
        inputs = {str(item).lower() for item in payload.get("inputs") or []}
        if "target" in required or "target" in inputs or "기업명 또는 종목코드" in payload.get("inputs", []):
            return True
    return False


def _companyPlan(api_ref: str, target: str, skill_refs: list[Ref], *, question: str) -> dict[str, Any]:
    if api_ref == "Company.analysis":
        subaxis = _analysisSubaxis(skill_refs)
        args = ["financial", subaxis] if subaxis else []
        return {"apiRef": api_ref, "target": target, "args": args, "question": question}
    return {"apiRef": api_ref, "target": target, "question": question}


def _analysisSubaxis(skill_refs: list[Ref]) -> str:
    for ref in skill_refs:
        skill_id = _skillId(ref)
        if not skill_id.startswith("engines.analysis."):
            continue
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        title = str(payload.get("title") or ref.title or "")
        cleaned = title.replace("Analysis -", "").replace("분석", "").strip(" -")
        if cleaned:
            return cleaned
    return ""


def _capabilityKeyFromSkills(skill_refs: list[Ref]) -> str:
    for ref in skill_refs:
        skill_id = _skillId(ref)
        parts = skill_id.split(".")
        if len(parts) >= 2 and parts[0] == "engines":
            return parts[1]
    return ""


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


def _requiredEvidence(state: WorkbenchState) -> list[str]:
    required: list[str] = []
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        required.extend(str(item) for item in payload.get("requiredEvidence") or [])
    return list(dict.fromkeys(required or ["skillRef", "apiRef"]))


def _requiresExecution(state: WorkbenchState) -> bool:
    required = set(_requiredEvidence(state))
    if required & _EVIDENCE_EXECUTION_NAMES:
        return True
    skill_ids = [_skillId(ref) for ref in state.selectedSkillRefs]
    return any(skill_id.startswith("engines.") for skill_id in skill_ids)


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


def _skillId(ref: Ref) -> str:
    if isinstance(ref.payload, dict) and ref.payload.get("id"):
        return str(ref.payload["id"])
    return ref.id.removeprefix("skill:")


def _chunks(text: str, *, size: int = 240) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]
