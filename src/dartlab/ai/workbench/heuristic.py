"""휴리스틱 흐름 — provider 가 LLM 이 아닐 때 5 패스 노드명을 발행하며 답을 합성.

BRIEF (profile + ReadSkill + ReadCapability + planEvidence) → WORK (EngineCall 루프)
→ COMPOSE (휴리스틱 답안) → GATE (verifyAnswer programmatic) → HARVEST (no-op).

본 모듈은 외부 LLM 의존 없음. targets / intent 의 정적 함수 + workbench tools 만 사용.
engineCall / verifyAnswer 는 registry 등록되어 있지 않고 직접 import — 휴리스틱 path 의
plan 실행 + GATE 검증은 LLM 도구 노출과 무관한 내부 helper 다.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from typing import Any

from dartlab.ai.contracts import Ref, TraceEvent
from dartlab.ai.tools.engineCall import engineCall
from dartlab.ai.tools.readCapability import readCapability
from dartlab.ai.tools.readSkill import readSkill
from dartlab.ai.tools.types import ToolResult
from dartlab.ai.tools.verifyAnswer import verifyAnswer

from .harvest import _wireMemory
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
    )
    activity_count = 0

    # ── BRIEF ──
    yield _node("brief", "질문 profile + skill/capability 후보를 만듭니다.", state)
    activity_count += 1
    state.profile = _buildQuestionProfile(state.question, stockCode=kwargs.get("stockCode"))
    state.intent = str(state.profile.get("taskType") or "research")

    yield _toolStart(state, "ReadSkill", {"query": state.question, "limit": 8})
    skill_result = readSkill(state.question, limit=8, includeBody=True)
    state.selectedSkillRefs = skill_result.refs
    state.refs.extend(skill_result.refs)
    state.toolCalls.append({"pass": "brief", "tool": "ReadSkill", "ok": skill_result.ok})
    yield _toolResult(state, "ReadSkill", skill_result)
    yield TraceEvent("reference", {"refs": [ref.toDict() for ref in skill_result.refs], "query": state.question})

    yield _toolStart(state, "ReadCapability", {"query": state.question, "limit": 10})
    spec_result = readCapability(state.question, limit=10)
    state.apiRefs = spec_result.refs
    state.refs.extend(spec_result.refs)
    state.toolCalls.append({"pass": "brief", "tool": "ReadCapability", "ok": spec_result.ok})
    yield _toolResult(state, "ReadCapability", spec_result)

    # selectedSkillRefs 의 requiredEvidence 통합 → state.requiredEvidence
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        for ev in payload.get("requiredEvidence") or []:
            if ev not in state.requiredEvidence:
                state.requiredEvidence.append(str(ev))

    state.plan = _planEvidence(state)
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
    yield _node("work", "EngineCall 실행 루프.", state)
    activity_count += 1
    results: list[dict[str, Any]] = []
    for index, plan in enumerate(state.plan, start=1):
        plan = _injectStepDependency(plan, results)
        yield _toolStart(state, plan["tool"], plan["args"])
        result = _executePlan(plan)
        state.toolCalls.append({"pass": "work", "tool": plan["tool"], "ok": result.ok, "summary": result.summary})
        state.refs.extend(result.refs)
        results.append({"plan": plan, "result": result})
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
                "refs": [ref.toDict() for ref in state.refs],
                "artifacts": [],
                "verification": {"ok": False, "issues": [state.failure], "refId": "verify:answer"},
                "responseMeta": {
                    "finalEvent": "unable",
                    "responseStatus": "failed",
                    "failureReason": state.failure,
                    "activityCount": activity_count,
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
            "refs": [ref.toDict() for ref in state.refs],
            "evidence": [ref.toDict() for ref in state.refs if ref.kind != "verifyRef"],
            "claims": list(state.claims),
            "artifacts": _harvestArtifacts(state),
            "verification": {"ok": True, "refId": "verify:answer"},
            "responseMeta": {
                "finalEvent": "answer",
                "responseStatus": "ok",
                "refCount": len(state.refs),
                "activityCount": activity_count,
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
            "artifacts": [ref.toDict() for ref in result.refs if ref.kind == "artifactRef"],
            "error": result.error,
        },
    )


# ── 실행 / 답변 합성 ──


def _executePlan(plan: dict[str, Any]) -> ToolResult:
    # plan dict 의 tool 필드는 PascalCase 가 정본. legacy snake (engine_call) 도 호환.
    tool = plan["tool"]
    if tool in ("EngineCall", "engine_call"):
        return engineCall(plan["args"].get("plan") or plan["args"])
    if tool == "ForensicsMemo":
        return _forensicsMemo(plan["args"])
    raise ValueError(f"unsupported workbench tool: {tool}")


def _forensicsMemo(args: dict[str, Any]) -> ToolResult:
    target = str(args.get("target") or "").strip()
    if not target:
        return ToolResult(False, "종목을 먼저 특정해야 포렌식 memo를 실행할 수 있습니다.", error="company_not_resolved")
    try:
        import polars as pl

        import dartlab
        from dartlab.synth.evidenceForensics import buildEvidenceForensicsMemo
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, f"forensics helper import 실패: {type(exc).__name__}", error="import_failed")

    try:
        with _quietForensicsExecution():
            company = dartlab.Company(target)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(False, f"{target} Company 객체 생성 실패: {type(exc).__name__}", error="company_failed")

    statements: dict[str, pl.DataFrame] = {}
    for topic in ("IS", "BS", "CF"):
        table = _safeShow(company, topic, pl=pl)
        if isinstance(table, pl.DataFrame) and table.height:
            statements[topic] = table

    section_texts: dict[str, str] = {}
    for topic in ("businessOverview", "riskFactors", "mdna", "notesDetail"):
        text = _safeTopicText(company, topic)
        if text:
            section_texts[topic] = text[:20000]

    events = _safeDisclosureEvents(company)
    scan_rows = _safeForensicsScanRows(dartlab)
    memo = buildEvidenceForensicsMemo(
        target=target,
        market=str(getattr(company, "market", "KR")),
        companyName=str(getattr(company, "corpName", getattr(company, "companyName", target))),
        statements=statements,
        sectionTexts=section_texts,
        events=events,
        scanRows=scan_rows,
    )
    refs = _forensicsRefs(target, memo)
    return ToolResult(
        True,
        f"{memo['companyName']} L1.5 포렌식 memo 실행",
        refs=refs,
        data={"memo": memo, "markdown": _forensicsMarkdown(memo)},
    )


def _safeShow(company: Any, topic: str, *, pl: Any) -> Any:
    try:
        with _quietForensicsExecution():
            table = company.show(topic, freq="Y")
    except TypeError:
        try:
            with _quietForensicsExecution():
                table = company.show(topic)
        except Exception:  # noqa: BLE001
            return pl.DataFrame()
    except Exception:  # noqa: BLE001
        return pl.DataFrame()
    return table if isinstance(table, pl.DataFrame) else pl.DataFrame()


def _safeTopicText(company: Any, topic: str) -> str:
    try:
        with _quietForensicsExecution():
            value = company.show(topic)
    except Exception:  # noqa: BLE001
        return ""
    return "" if value is None else str(value)


def _safeDisclosureEvents(company: Any) -> list[dict[str, Any]]:
    try:
        with _quietForensicsExecution():
            disclosure = company.disclosure()
    except Exception:  # noqa: BLE001
        return []
    if hasattr(disclosure, "head") and hasattr(disclosure, "to_dicts"):
        try:
            with _quietForensicsExecution():
                return list(disclosure.head(20).to_dicts())
        except Exception:  # noqa: BLE001
            return []
    try:
        return [row for row in list(disclosure)[:20] if isinstance(row, dict)]
    except Exception:  # noqa: BLE001
        return []


def _safeForensicsScanRows(dartlab_module: Any) -> list[dict[str, Any]]:
    if os.environ.get("DARTLAB_FORENSICS_SCAN", "0") not in {"1", "true", "True"}:
        return []
    rows: list[dict[str, Any]] = []
    for axis in ("quality", "audit", "disclosureRisk"):
        try:
            with _quietForensicsExecution():
                frame = dartlab_module.scan(axis)
                if not hasattr(frame, "head") or not hasattr(frame, "to_dicts"):
                    continue
                axis_rows = frame.head(3).to_dicts()
        except Exception:  # noqa: BLE001
            continue
        for row in axis_rows:
            if isinstance(row, dict):
                item = dict(row)
                item["axis"] = axis
                rows.append(item)
    return rows


@contextmanager
def _quietForensicsExecution() -> Iterator[None]:
    previous_disable = logging.root.manager.disable
    logging.disable(logging.INFO)
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            yield
    finally:
        logging.disable(previous_disable)


def _forensicsRefs(target: str, memo: dict[str, Any]) -> list[Ref]:
    as_of = str(memo.get("asOf") or "unknown")
    refs: list[Ref] = []
    for table_name, rows in (memo.get("tables") or {}).items():
        if not isinstance(rows, list):
            continue
        refs.append(
            Ref(
                id=f"table:forensics:{target}:{table_name}:{as_of}",
                kind="tableRef",
                title=f"{memo.get('companyName') or target} {table_name}",
                source="buildEvidenceForensicsMemo",
                payload={"table": table_name, "rows": rows, "period": as_of},
            )
        )
    headline = memo.get("headline") or {}
    for key in ("riskScore", "signalCount", "candidateCount"):
        refs.append(
            Ref(
                id=f"value:forensics:{target}:{key}:{as_of}",
                kind="valueRef",
                title=f"{key} {headline.get(key)}",
                source=f"table:forensics:{target}:deepDive:{as_of}",
                payload={"metric": key, "value": headline.get(key), "period": as_of},
            )
        )
    refs.append(
        Ref(
            id=f"date:forensics:{target}:{as_of}",
            kind="dateRef",
            title="forensics memo 기준시점",
            source=f"table:forensics:{target}:deepDive:{as_of}",
            payload={"period": as_of},
        )
    )
    for source in memo.get("sources") or []:
        if isinstance(source, dict):
            refs.append(
                Ref(
                    id=f"source:forensics:{target}:{source.get('id')}",
                    kind="sourceRef",
                    title=str(source.get("title") or source.get("id") or "source"),
                    source=str(source.get("url") or ""),
                    payload=source,
                )
            )
    return refs


def _forensicsMarkdown(memo: dict[str, Any]) -> str:
    headline = memo.get("headline") or {}
    tables = memo.get("tables") or {}
    cash = (tables.get("revenueToCashBridge") or [{}])[0]
    wc = (tables.get("workingCapitalPressureMap") or [{}])[0]
    note_risks = [row for row in tables.get("noteSignalExtractor", []) if row.get("status") in {"watch", "risk"}][:5]
    falsifiers = tables.get("falsifierLedger") or []
    candidates = tables.get("engineCandidateMemo") or []
    deep = tables.get("deepDive") or []

    lines = [
        f"{memo.get('companyName') or memo.get('target')} L1.5 포렌식 deep dive 결과입니다.",
        "",
        "L2 분석엔진은 호출하지 않았고, Company.show 원표, 공시/섹션 텍스트, optional scan primitive와 L1.5 helper만 사용했습니다.",
        f"기준시점은 {memo.get('asOf')}이며, 이 결과는 투자 결론이 아니라 원표 기반 검산 ledger입니다.",
        "",
        "## Headline",
        f"- riskScore: {headline.get('riskScore')}",
        f"- signalCount: {headline.get('signalCount')}",
        f"- candidateCount: {headline.get('candidateCount')}",
        f"- decisionStatus: {headline.get('decisionStatus')}",
        "",
        "## 원표 신호",
        f"- revenue-cash: {cash.get('status')} / 매출채권 증가율-매출 증가율 {cash.get('receivableGrowthMinusRevenueGrowth')}",
        f"- working capital: {wc.get('status')} / CCC {wc.get('cccDays')}, 재고 gap {wc.get('inventoryGrowthMinusRevenueGrowth')}",
        "",
        "## 공시 텍스트 신호",
    ]
    if note_risks:
        for row in note_risks:
            lines.append(f"- {row.get('signal')}: {row.get('status')} / hitCount {row.get('hitCount')}")
    else:
        lines.append("- watch/risk 키워드 신호는 현재 입력 범위에서 확인되지 않았습니다.")

    lines.extend(["", "## Falsifier Ledger"])
    for row in falsifiers:
        lines.append(f"- {row.get('claim')}: {row.get('status')} / 필요한 반증: {row.get('counterEvidenceNeeded')}")

    lines.extend(["", "## Engine Candidate Memo"])
    for row in candidates:
        lines.append(f"- {row.get('signalId')}: {row.get('status')} / owner 후보 {row.get('recommendedEngineOwner')}")

    lines.extend(["", "## Deep Dive 단계"])
    for row in deep:
        lines.append(f"- {row.get('order')}. {row.get('step')}: {row.get('status')} / {row.get('nextAction')}")

    lines.append("")
    lines.append("답변 근거는 tableRef, valueRef, dateRef, sourceRef로 분리해 남겼습니다.")
    return "\n".join(lines)


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
        """find — TODO 한국어 동작 설명."""
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
        for apiRef, summary in api_rows:
            lines.append(f"- {apiRef}: {summary}")
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
    if tool in ("EngineCall", "engine_call"):
        plan = args.get("plan") or args
        apiRef = plan.get("apiRef") or f"{plan.get('engine')}.{plan.get('method')}"
        target = plan.get("target") or plan.get("axis") or plan.get("path") or ""
        return f"{apiRef} {target}".strip()
    return str(args.get("query") or args.get("target") or tool)


def _harvestArtifacts(state: WorkbenchState) -> list[dict[str, Any]]:
    return [ref.toDict() for ref in state.refs if ref.kind == "artifactRef"]


def _chunks(text: str, *, size: int = 240) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]
