"""Ask Workbench Kernel.

The kernel is not a collection of financial answer scripts.  It only owns the
request session, workbench action dispatch, refs, verification, and answer
release. Financial analysis must be performed through provider-selected
workbench actions such as `inspect_dataset` and `run_python`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .contracts import AnswerDraft, Ref, ResultBundle, TraceEvent, VerificationResult, WorkbenchTask, new_id
from .datasets import inspect_dataset, inspection_to_refs
from .notebook import execution_to_ref, run_python
from .providers import ToolCall, WorkbenchProvider, create_provider
from .reference import read_context, search_reference
from .verify import verification_to_ref, verify_answer
from .visuals import compile_visual, visual_to_ref

_MAX_WORKBENCH_ROUNDS = 12
_MAX_REPAIR_ROUNDS = 3


@dataclass
class AskSession:
    question: str
    kwargs: dict[str, Any] = field(default_factory=dict)
    refs: list[Ref] = field(default_factory=list)
    trace: list[TraceEvent] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    visuals: list[dict[str, Any]] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)

    def add_event(self, kind: str, data: dict[str, Any]) -> TraceEvent:
        event = TraceEvent(kind=kind, data=data)
        self.trace.append(event)
        return event

    def add_ref(self, ref: Ref) -> Ref:
        self.refs.append(ref)
        return ref


def runAsk(question: Any, *args: Any, stream: bool = True, **kwargs: Any) -> Iterable[TraceEvent]:
    """Ask Workbench 실행 — LLM 이 DartLab 을 읽고 실행한 뒤 답변.

    Description
    -----------
    공개 AI 진입점의 단일 kernel 이다. 질문을 금융 유형으로 분류하지 않고,
    provider 에게 workbench action 을 제공한 뒤 LLM 이 제출한 최종 답변을
    ref 기반으로 검산한다.

    Parameters
    ----------
    question : Any
        사용자 질문. Company 인스턴스와 함께 호출된 경우 첫 위치 인자를 질문으로
        해석하고 회사 정보는 힌트로만 보관한다.
    *args : Any
        하위호환 위치 인자.
    stream : bool, optional
        True 면 TraceEvent stream 을 반환한다.
    **kwargs : Any
        provider, model, role, api_key, base_url 등 provider 설정.

    Returns
    -------
    Iterable[TraceEvent]
        kind : str — task/reference/inspect/execute/visual/verify/chunk/done/error
        data : dict — 이벤트별 payload

    Raises
    ------
    없음
        provider 오류는 error event 와 done bundle 의 limits 로 노출한다.

    Examples
    --------
    >>> events = list(runAsk("최근 주가지수를 보고 강세 지수를 찾아봐라"))
    >>> events[-1].kind
    'done'

    Notes
    -----
    Kernel 은 질문별 Python 코드나 답변 템플릿을 갖지 않는다.

    Guide
    -----
    새 분석 능력은 kernel 분기가 아니라 DartLab docstring/capabilities 와
    실행 가능한 Python API 개선으로 추가한다.

    See Also
    --------
    ask : 텍스트 응답용 wrapper.
    verify_answer : 최종 답변 claim 검산.
    """

    question_text, kwargs = _normalize_question(question, args, kwargs)
    session = AskSession(question=question_text, kwargs=kwargs)
    task = create_task(question_text, kwargs)
    yield session.add_event("task", {"task": task.to_dict()})

    refs = search_reference(question_text, limit=5)
    for ref in refs:
        session.add_ref(ref)
    yield session.add_event("reference", _reference_event_payload(refs))

    try:
        provider = create_provider(**kwargs)
    except Exception as exc:
        yield session.add_event("error", {"error": "provider_create_failed", "detail": str(exc)})
        yield from _finalize_provider_unavailable(session, reason=str(exc))
        return

    check_available = getattr(provider, "check_available", None)
    if callable(check_available) and not check_available():
        config = getattr(provider, "config", None)
        reason = f"provider unavailable: {getattr(config, 'provider', None) or 'unknown'}"
        session.limits.append(reason)
        yield from _finalize_provider_unavailable(session, reason=reason)
        return

    try:
        completed = False
        for event in _run_provider_workbench(session, task, provider):
            completed = completed or event.kind == "done"
            yield event
        if completed:
            return
        session.limits.append("provider workbench ended without finalize_answer")
    except Exception as exc:
        session.limits.append(f"provider transport failed: {exc}")
        yield session.add_event("error", {"error": "provider_transport_failed", "detail": str(exc)})

    yield from _finalize_unable_to_finalize(session, reason="provider did not produce a verified final answer")


def ask(question: str, *, stream: bool = True, **kwargs: Any) -> str | Iterable[str]:
    """텍스트 Ask 실행 — TraceEvent stream 을 사용자 응답으로 변환.

    Description
    -----------
    `runAsk()`의 chunk 이벤트만 소비해 텍스트 응답을 반환한다. stream=True 면
    chunk 문자열 제너레이터를 반환하고, stream=False 면 전체 문자열을 반환한다.

    Parameters
    ----------
    question : str
        사용자 질문.
    stream : bool, optional
        True 면 응답 chunk 제너레이터, False 면 전체 응답 문자열.
    **kwargs : Any
        provider, model, role, api_key, base_url 등 provider 설정.

    Returns
    -------
    str | Iterable[str]
        str — stream=False 일 때 최종 답변 텍스트
        Iterable[str] — stream=True 일 때 답변 chunk 목록

    Raises
    ------
    없음
        provider/tool 오류는 응답 limits 와 trace 에 포함된다.

    Examples
    --------
    >>> dartlab.ask("너 뭐 분석할수있나", stream=False)
    '...'

    Notes
    -----
    분석 실행과 검산은 `runAsk()`가 담당한다.

    Guide
    -----
    서버, CLI, UI는 가능하면 `runAsk()` trace 를 직접 소비한다.

    See Also
    --------
    runAsk : Ask Workbench Kernel 기본 실행 함수.
    """

    events = runAsk(question, stream=stream, **kwargs)
    if stream:
        return _chunk_text(events)
    chunks: list[str] = []
    for event in events:
        if event.kind == "chunk":
            chunks.append(event.data.get("text", ""))
    return "".join(chunks)


def create_task(question: str, kwargs: dict[str, Any] | None = None) -> WorkbenchTask:
    return WorkbenchTask(
        id=new_id("task"),
        question=question,
    )



def _run_provider_workbench(session: AskSession, task: WorkbenchTask, provider: WorkbenchProvider) -> Iterable[TraceEvent]:
    messages = _initial_provider_messages(session, task)
    tools = _provider_tool_specs()
    repair_count = 0
    for _round in range(_MAX_WORKBENCH_ROUNDS):
        turn = provider.generate(messages, tools)
        messages.append(_assistant_message(turn.content, turn.tool_calls))
        if not turn.tool_calls:
            if turn.content.strip():
                draft = AnswerDraft(
                    answer=turn.content.strip(),
                    evidence_refs=[ref.id for ref in session.refs],
                    limits=session.limits + ["provider returned prose without finalize_answer; kernel verified it as a draft"],
                )
                verification = verify_answer(task, session.refs, draft)
                if not verification.ok and repair_count < _MAX_REPAIR_ROUNDS:
                    repair_count += 1
                    messages.append(_repair_message(verification, "prose_without_finalize"))
                    continue
                yield from _finalize(session, task, draft)
                return
            continue
        for call in turn.tool_calls:
            if call.name == "finalize_answer":
                draft = _draft_from_tool_args(call.args, session)
                verification = verify_answer(task, session.refs, draft)
                if not verification.ok and repair_count < _MAX_REPAIR_ROUNDS:
                    repair_count += 1
                    messages.append(_repair_message(verification, "finalize_answer_failed"))
                    continue
                yield from _finalize(session, task, draft)
                return
            try:
                result, events = _execute_workbench_action(session, call.name, call.args)
            except Exception as exc:
                result = {"ok": False, "error": str(exc), "action": call.name}
                session.limits.append(f"tool {call.name} failed: {exc}")
                events = [session.add_event("error", {"error": "tool_failed", "action": call.name, "detail": str(exc)})]
            for event in events:
                yield event
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _tool_result_content(session, result)})
    yield from _force_finalize(session, task, provider, messages)


def _execute_workbench_action(session: AskSession, name: str, args: dict[str, Any]) -> tuple[dict[str, Any], list[TraceEvent]]:
    events: list[TraceEvent] = []
    if name == "search_reference":
        refs = search_reference(str(args.get("query") or session.question), limit=int(args.get("limit") or 5))
        for ref in refs:
            session.add_ref(ref)
        events.append(session.add_event("reference", {"action": name, **_reference_event_payload(refs)}))
        return {"refs": [ref.to_dict() for ref in refs]}, events
    if name == "read_context":
        ref = read_context(
            str(args.get("path") or ""),
            start_line=int(args.get("start_line") or args.get("startLine") or 1),
            max_chars=int(args.get("max_chars") or args.get("maxChars") or 4000),
        )
        session.add_ref(ref)
        events.append(session.add_event("reference", {"action": name, "ref": ref.to_dict()}))
        return {"ref": ref.to_dict()}, events
    if name == "inspect_dataset":
        inspection = inspect_dataset(str(args.get("target") or ""), sample=int(args.get("sample") or 5), columns=args.get("columns"))
        refs = inspection_to_refs(inspection)
        for ref in refs:
            session.add_ref(ref)
        events.append(session.add_event("inspect", {"action": name, "target": args.get("target"), "result": inspection.to_dict()}))
        return {"inspection": inspection.to_dict(), "refs": [ref.to_dict() for ref in refs]}, events
    if name == "run_python":
        execution = run_python(str(args.get("code") or ""), timeout=int(args.get("timeout") or 60))
        ref = session.add_ref(execution_to_ref(execution))
        derived_refs = _refs_from_execution(execution, ref.id)
        session.limits.extend(_limits_from_execution(execution))
        for derived_ref in derived_refs:
            session.add_ref(derived_ref)
        events.append(session.add_event("execute", {"action": name, "refId": ref.id, "result": execution.to_dict()}))
        return {"execution": execution.to_dict(), "ref": ref.to_dict(), "derivedRefs": [r.to_dict() for r in derived_refs]}, events
    if name == "compile_visual":
        source_ref = str(args.get("source_ref") or args.get("sourceRef") or "")
        source_ref, rows, category, metric = _visual_inputs_from_refs(
            session,
            source_ref=source_ref,
            rows=list(args.get("rows") or []),
            category=str(args.get("category") or ""),
            metric=str(args.get("metric") or ""),
        )
        visual = compile_visual(
            source_ref=source_ref,
            rows=rows,
            category=category,
            metric=metric,
            purpose=str(args.get("purpose") or "comparison"),
            title=args.get("title"),
            as_of=args.get("as_of") or args.get("asOf"),
        )
        session.visuals.append(visual.to_dict())
        ref = session.add_ref(visual_to_ref(visual))
        events.append(session.add_event("visual", {"action": name, "visuals": [visual.to_dict()], "refId": ref.id}))
        return {"visual": visual.to_dict(), "ref": ref.to_dict()}, events
    return {"ok": False, "error": f"unknown workbench action: {name}"}, events


def _initial_provider_messages(session: AskSession, task: WorkbenchTask) -> list[dict[str, Any]]:
    task_capsule = {
        "kernel": "Ask Workbench Kernel",
        "question": session.question,
        "task": task.to_dict(),
        "basicSkills": _basic_skill_capsule(),
        "rules": [
            "Search references for relevant tools, capabilities, skills, knowledge, and runtime datasets.",
            "When search_reference returns skill refs, use them as reusable procedures: collect their requiredEvidence before strong judgment.",
            "Use inspect_dataset before making dataset/date claims.",
            "Use run_python when your answer depends on computed DartLab results.",
            "Inside run_python, use Polars (`pl`) for parquet/csv work; `pl` is pre-imported.",
            "When run_python produces answer evidence, call emit_result(rows=..., values=..., units=..., formulas=..., inputs=..., meta=..., limits=...).",
            "Use compile_visual only for table-backed visuals.",
            "Call finalize_answer only after refs support material claims.",
            "Never say current date when you mean dataset asOf.",
        ],
        "availableRefs": [ref.to_dict() for ref in session.refs],
    }
    return [
        {
            "role": "system",
            "content": (
                "You are operating DartLab's financial analysis workbench. "
                "Do not answer from memorized financial patterns. Ground each judgment in DartLab's "
                "real references, runtime datasets, Python execution results, and verification refs. "
                "Use workbench tools to inspect, execute, verify, and finalize."
            ),
        },
        {"role": "user", "content": json.dumps(task_capsule, ensure_ascii=False, default=str)},
    ]


def _basic_skill_capsule() -> list[dict[str, Any]]:
    try:
        from dartlab.skills import listSkills
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for spec in listSkills(includeUser=False):
        if getattr(spec, "category", None) != "basic":
            continue
        out.append(
            {
                "id": spec.id,
                "title": spec.title,
                "category": spec.category,
                "purpose": spec.purpose,
                "whenToUse": spec.whenToUse[:4],
                "capabilityRefs": spec.capabilityRefs[:12],
                "requiredEvidence": spec.requiredEvidence,
                "expectedOutputs": spec.expectedOutputs,
            }
        )
    return out


def _reference_event_payload(refs: list[Ref]) -> dict[str, Any]:
    return {
        "refs": [ref.to_dict() for ref in refs],
        "selectedSkillCandidates": _candidate_summary(refs, kind="skill"),
        "selectedCapabilityCandidates": _candidate_summary(refs, kind="capability"),
    }


def _candidate_summary(refs: list[Ref], *, kind: str, limit: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        if ref.kind != kind:
            continue
        payload = ref.payload
        item: dict[str, Any]
        if kind == "skill":
            item = {
                "id": payload.get("skillId"),
                "category": payload.get("category"),
                "score": payload.get("score"),
                "reasons": payload.get("reasons", []),
                "capabilityRefs": payload.get("capabilityRefs", [])[:8],
            }
        else:
            item = {
                "id": payload.get("apiRef"),
                "score": payload.get("score"),
                "summary": payload.get("summary"),
            }
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _provider_tool_specs(*, finalize_only: bool = False) -> list[dict[str, Any]]:
    def tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required or [],
                    "additionalProperties": True,
                },
            },
        }

    finalize_tool = tool(
        "finalize_answer",
        "Submit the final answer draft for deterministic verification and release.",
        {
            "answer": {"type": "string"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "material_claims": {"type": "array", "items": {"type": "object"}},
            "visual_refs": {"type": "array", "items": {"type": "string"}},
            "limits": {"type": "array", "items": {"type": "string"}},
        },
        ["answer"],
    )
    if finalize_only:
        return [finalize_tool]
    return [
        tool("search_reference", "Search DartLab tools, capabilities, skills, knowledge, docs, and runtime dataset catalog; returns short refs.", {"query": {"type": "string"}, "limit": {"type": "integer"}}, ["query"]),
        tool("read_context", "Read a bounded source text window inside the workspace.", {"path": {"type": "string"}, "start_line": {"type": "integer"}, "max_chars": {"type": "integer"}}, ["path"]),
        tool("inspect_dataset", "Inspect runtime dataset id or parquet/csv path.", {"target": {"type": "string"}, "sample": {"type": "integer"}, "columns": {"type": "array", "items": {"type": "string"}}}, ["target"]),
        tool(
            "run_python",
            "Run bounded Python code in the DartLab workspace. Polars is available as `pl`; use emit_result(...) for evidence refs.",
            {"code": {"type": "string"}, "timeout": {"type": "integer"}},
            ["code"],
        ),
        tool(
            "compile_visual",
            "Compile a validated chart from table rows; single-value visuals are rejected.",
            {
                "source_ref": {"type": "string"},
                "rows": {"type": "array", "items": {"type": "object"}},
                "category": {"type": "string"},
                "metric": {"type": "string"},
                "purpose": {"type": "string"},
                "title": {"type": "string"},
                "as_of": {"type": "string"},
            },
            ["source_ref", "rows", "category", "metric"],
        ),
        finalize_tool,
    ]


def _assistant_message(content: str, tool_calls: list[ToolCall]) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content or None}
    if tool_calls:
        message["tool_calls"] = [
            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.args, ensure_ascii=False)}}
            for call in tool_calls
        ]
    return message


def _repair_message(verification: VerificationResult, reason: str) -> dict[str, Any]:
    return {
        "role": "user",
        "content": json.dumps(
            {
                "type": "verification_failed",
                "reason": reason,
                "issues": verification.issues,
                "instruction": (
                    "Do not repeat unsupported prose or tool-call transcripts. Use workbench actions to create refs, "
                    "call emit_result(...) from run_python when needed, or submit a narrower finalize_answer "
                    "whose numeric/date/visual claims are supported."
                ),
            },
            ensure_ascii=False,
            default=str,
        ),
    }


def _force_finalize(
    session: AskSession,
    task: WorkbenchTask,
    provider: WorkbenchProvider,
    messages: list[dict[str, Any]],
) -> Iterable[TraceEvent]:
    messages.append(_finalize_request_message(session))
    tools = _provider_tool_specs(finalize_only=True)
    for _attempt in range(2):
        turn = provider.generate(messages, tools)
        messages.append(_assistant_message(turn.content, turn.tool_calls))
        for call in turn.tool_calls:
            if call.name != "finalize_answer":
                continue
            draft = _draft_from_tool_args(call.args, session)
            verification = verify_answer(task, session.refs, draft)
            if not verification.ok:
                messages.append(_repair_message(verification, "forced_finalize_failed"))
                break
            yield from _finalize(session, task, draft)
            return
        if turn.content.strip():
            draft = AnswerDraft(
                answer=turn.content.strip(),
                evidence_refs=[ref.id for ref in session.refs],
                visual_refs=[ref.id for ref in session.refs if ref.kind == "visual"],
                limits=session.limits + ["provider returned prose in forced finalize; kernel verified it as a draft"],
            )
            verification = verify_answer(task, session.refs, draft)
            if verification.ok:
                yield from _finalize(session, task, draft)
                return
            messages.append(_repair_message(verification, "forced_finalize_prose_failed"))
    yield from _finalize_unable_to_finalize(session, reason="provider could not submit a verified finalize_answer")


def _finalize_request_message(session: AskSession) -> dict[str, Any]:
    compact_refs = [
        {"id": ref.id, "kind": ref.kind, "source": ref.source}
        for ref in session.refs
        if ref.kind in {"dataset", "date", "execution", "table", "value", "visual"}
    ][-20:]
    return {
        "role": "user",
        "content": json.dumps(
            {
                "type": "finalize_required",
                "instruction": "Stop calling analysis tools. Use finalize_answer now with only claims supported by these refs.",
                "refs": compact_refs,
                "limits": session.limits,
            },
            ensure_ascii=False,
            default=str,
        ),
    }


def _tool_result_content(session: AskSession, result: dict[str, Any]) -> str:
    payload = {
        "result": result,
        "refLedger": _compact_ref_ledger(session),
        "limits": session.limits[-10:],
    }
    text = json.dumps(payload, ensure_ascii=False, default=str)
    if len(text) > 24_000:
        text = text[:24_000] + "\n...[truncated]"
    return text


def _compact_ref_ledger(session: AskSession) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in session.refs[-30:]:
        item: dict[str, Any] = {"id": ref.id, "kind": ref.kind, "source": ref.source}
        if ref.kind == "dataset":
            item["datasetId"] = ref.payload.get("dataset_id") or ref.payload.get("datasetId")
            item["path"] = ref.payload.get("path")
        elif ref.kind == "date":
            item["observedDate"] = ref.payload.get("observedDate")
        elif ref.kind == "execution":
            item["ok"] = ref.payload.get("ok")
            item["returncode"] = ref.payload.get("returncode")
        elif ref.kind == "table":
            rows = ref.payload.get("rows")
            item["rows"] = len(rows) if isinstance(rows, list) else None
            item["metric"] = ref.payload.get("metric")
            item["executionRef"] = ref.payload.get("executionRef")
        elif ref.kind == "value":
            item["name"] = ref.payload.get("name")
            item["value"] = ref.payload.get("value")
        elif ref.kind == "visual":
            item["sourceRef"] = ref.payload.get("sourceRef")
            item["metric"] = ref.payload.get("metric")
        out.append(item)
    return out


def _draft_from_tool_args(args: dict[str, Any], session: AskSession) -> AnswerDraft:
    evidence_refs = [str(v) for v in args.get("evidence_refs") or args.get("evidenceRefs") or []]
    visual_refs = [str(v) for v in args.get("visual_refs") or args.get("visualRefs") or []]
    if not evidence_refs:
        evidence_refs = [ref.id for ref in session.refs if ref.kind != "verify"]
    if not visual_refs:
        visual_refs = [ref.id for ref in session.refs if ref.kind == "visual"]
    claims = args.get("material_claims") or args.get("materialClaims") or []
    limits = args.get("limits") or []
    return AnswerDraft(
        answer=str(args.get("answer") or ""),
        evidence_refs=evidence_refs,
        material_claims=[claim for claim in claims if isinstance(claim, dict)] if isinstance(claims, list) else [],
        visual_refs=visual_refs,
        limits=session.limits + ([str(v) for v in limits] if isinstance(limits, list) else [str(limits)]),
    )


def _visual_inputs_from_refs(
    session: AskSession,
    *,
    source_ref: str,
    rows: list[Any],
    category: str,
    metric: str,
) -> tuple[str, list[dict[str, Any]], str, str]:
    clean_rows = [row for row in rows if isinstance(row, dict)]
    if len(clean_rows) >= 2 and category and metric and _has_visual_values(clean_rows, category, metric):
        return source_ref, clean_rows, category, metric
    table_ref = _find_table_ref(session.refs, source_ref)
    if table_ref is None:
        return source_ref, clean_rows, category, metric
    source_ref = source_ref or table_ref.id
    table_rows = table_ref.payload.get("rows")
    if isinstance(table_rows, list) and len(table_rows) >= 2 and all(isinstance(row, dict) for row in table_rows):
        clean_rows = table_rows
    if not metric or not _has_numeric_key(clean_rows, metric):
        metric = str(table_ref.payload.get("metric") or "")
    if not metric or not _has_numeric_key(clean_rows, metric):
        metric = _first_numeric_key(clean_rows) or metric
    if not category or not any(category in row for row in clean_rows):
        category = _first_category_key(clean_rows, metric)
    return source_ref, clean_rows, category, metric


def _find_table_ref(refs: list[Ref], source_ref: str) -> Ref | None:
    for ref in refs:
        if ref.kind == "table" and ref.id == source_ref:
            return ref
    for ref in refs:
        if ref.kind == "table" and ref.payload.get("executionRef") == source_ref:
            return ref
    for ref in reversed(refs):
        if ref.kind == "table":
            return ref
    return None


def _first_category_key(rows: list[dict[str, Any]], metric: str) -> str:
    if not rows:
        return ""
    for key, value in rows[0].items():
        if key == metric:
            continue
        if isinstance(value, str):
            return key
    for key in rows[0]:
        if key != metric:
            return key
    return ""


def _has_visual_values(rows: list[dict[str, Any]], category: str, metric: str) -> bool:
    count = 0
    for row in rows:
        if category not in row or metric not in row:
            continue
        try:
            float(str(row[metric]).replace(",", ""))
        except (TypeError, ValueError):
            continue
        count += 1
    return count >= 2


def _has_numeric_key(rows: list[dict[str, Any]], key: str) -> bool:
    if not key:
        return False
    for row in rows:
        if key not in row:
            continue
        try:
            float(str(row[key]).replace(",", ""))
            return True
        except (TypeError, ValueError):
            continue
    return False


def _finalize_provider_unavailable(session: AskSession, *, reason: str) -> Iterable[TraceEvent]:
    result = VerificationResult(
        ok=False,
        issues=[{"code": "provider_unavailable", "message": reason}],
        passed_checks=[],
    )
    verify_ref = verification_to_ref(result)
    session.add_ref(verify_ref)
    yield session.add_event("verify", {"refId": verify_ref.id, "result": result.to_dict()})
    answer = (
        "AI provider가 현재 workbench 실행을 완료하지 못했습니다. "
        "답변을 추정하지 않고 중단합니다."
    )
    for chunk in _stream_chunks(answer):
        yield session.add_event("chunk", {"text": chunk})
    bundle = ResultBundle(
        answer=answer,
        artifacts=session.artifacts,
        refs=[ref.to_dict() for ref in session.refs],
        trace=[event.to_dict() for event in session.trace],
        verification=result.to_dict(),
        visuals=session.visuals,
        limits=[*session.limits, "provider_unavailable"],
        response_meta={
            "kernel": "Ask Workbench Kernel",
            "refCount": len(session.refs),
            "verificationOk": False,
        },
    )
    yield session.add_event("done", bundle.to_dict())


def _finalize_unable_to_finalize(session: AskSession, *, reason: str) -> Iterable[TraceEvent]:
    result = VerificationResult(
        ok=False,
        issues=[{"code": "unable_to_finalize", "message": reason}],
        passed_checks=[],
    )
    verify_ref = verification_to_ref(result)
    session.add_ref(verify_ref)
    yield session.add_event("verify", {"refId": verify_ref.id, "result": result.to_dict()})
    answer = "검증을 통과한 최종 답변을 만들지 못했습니다. 근거 없는 답변을 내보내지 않습니다."
    for chunk in _stream_chunks(answer):
        yield session.add_event("chunk", {"text": chunk})
    bundle = ResultBundle(
        answer=answer,
        artifacts=session.artifacts,
        refs=[ref.to_dict() for ref in session.refs],
        trace=[event.to_dict() for event in session.trace],
        verification=result.to_dict(),
        visuals=session.visuals,
        limits=[*session.limits, "unable_to_finalize"],
        response_meta={
            "kernel": "Ask Workbench Kernel",
            "refCount": len(session.refs),
            "verificationOk": False,
        },
    )
    yield session.add_event("done", bundle.to_dict())


def _finalize(session: AskSession, task: WorkbenchTask, draft: AnswerDraft) -> Iterable[TraceEvent]:
    verification = verify_answer(task, session.refs, draft)
    verify_ref = verification_to_ref(verification)
    session.add_ref(verify_ref)
    yield session.add_event("verify", {"refId": verify_ref.id, "result": verification.to_dict()})

    answer = draft.answer if verification.ok else _verification_failed_answer(verification.issues)
    for chunk in _stream_chunks(answer):
        yield session.add_event("chunk", {"text": chunk})

    bundle = ResultBundle(
        answer=answer,
        artifacts=session.artifacts,
        refs=[ref.to_dict() for ref in session.refs],
        trace=[event.to_dict() for event in session.trace],
        verification=verification.to_dict(),
        visuals=session.visuals,
        limits=[*draft.limits, *[issue.get("code", "verification_issue") for issue in verification.issues]],
        response_meta={
            "kernel": "Ask Workbench Kernel",
            "refCount": len(session.refs),
            "verificationOk": verification.ok,
        },
    )
    yield session.add_event("done", bundle.to_dict())


def _normalize_question(question: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(question, str):
        return question, kwargs
    if args and isinstance(args[0], str):
        if question is not None:
            kwargs.setdefault("company", getattr(question, "stockCode", None) or getattr(question, "corpName", None))
        return args[0], kwargs
    return str(question or ""), kwargs


def _stream_chunks(answer: str, size: int = 240) -> Iterable[str]:
    for i in range(0, len(answer), size):
        yield answer[i : i + size]


def _chunk_text(events: Iterable[TraceEvent]) -> Iterable[str]:
    for event in events:
        if event.kind == "chunk":
            yield event.data.get("text", "")


def _verification_failed_answer(issues: list[dict[str, Any]]) -> str:
    issue_codes = ", ".join(str(issue.get("code")) for issue in issues)
    return "검증을 통과한 답변을 만들지 못했습니다. 근거 없는 최종 답변을 내보내지 않습니다." + (
        f"\n\n검증 실패: {issue_codes}" if issue_codes else ""
    )


def _refs_from_execution(execution: Any, execution_ref_id: str) -> list[Ref]:
    refs: list[Ref] = []
    if not getattr(execution, "ok", False):
        return refs
    payload = _extract_result_json(getattr(execution, "stdout", ""))
    if not isinstance(payload, dict):
        return refs
    rows = payload.get("rows")
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    units = payload.get("units") if isinstance(payload.get("units"), dict) else {}
    formulas = payload.get("formulas") if isinstance(payload.get("formulas"), dict) else {}
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), list) else []
    if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
        metric = _table_metric_from_payload(rows, payload, meta)
        table_ref = Ref(
            id=new_id("table"),
            kind="table",
            source="run_python",
            payload={
                "executionRef": execution_ref_id,
                "rows": rows,
                "metric": metric,
                "unit": units.get(metric) if metric else None,
                "formula": formulas.get(metric) if metric else None,
                "inputRefs": inputs,
                "meta": meta,
            },
        )
        refs.append(table_ref)
    as_of = payload.get("asOf") or payload.get("as_of") or payload.get("observedDate") or meta.get("asOf") or meta.get("as_of") or meta.get("observedDate")
    if as_of:
        refs.append(
            Ref(
                id=new_id("date"),
                kind="date",
                source="run_python",
                payload={"executionRef": execution_ref_id, "observedDate": str(as_of), "basis": "execution result meta"},
            )
        )
    values = payload.get("values")
    if isinstance(values, dict):
        for key, value in values.items():
            if isinstance(value, (int, float)):
                refs.append(
                    Ref(
                        id=new_id("value"),
                        kind="value",
                        source="run_python",
                        payload={
                            "executionRef": execution_ref_id,
                            "name": str(key),
                            "metric": str(key),
                            "value": value,
                            "unit": units.get(str(key)),
                            "formula": formulas.get(str(key)),
                            "inputRefs": inputs,
                            "period": meta.get("period"),
                            "asOf": meta.get("asOf") or meta.get("as_of") or meta.get("observedDate"),
                            "target": meta.get("target"),
                        },
                    )
                )
    for key, value in payload.items():
        if key in {"rows", "meta", "limits", "units", "formulas", "inputs"}:
            continue
        if isinstance(value, (int, float)):
            refs.append(
                Ref(
                    id=new_id("value"),
                    kind="value",
                    source="run_python",
                    payload={
                        "executionRef": execution_ref_id,
                        "name": key,
                        "metric": key,
                        "value": value,
                        "unit": units.get(key),
                        "formula": formulas.get(key),
                        "inputRefs": inputs,
                        "period": meta.get("period"),
                        "asOf": meta.get("asOf") or meta.get("as_of") or meta.get("observedDate"),
                        "target": meta.get("target"),
                    },
                )
            )
    return refs


def _limits_from_execution(execution: Any) -> list[str]:
    payload = _extract_result_json(getattr(execution, "stdout", ""))
    if not isinstance(payload, dict):
        return []
    raw_limits = payload.get("limits")
    if isinstance(raw_limits, list):
        return [str(item) for item in raw_limits if item is not None]
    if isinstance(raw_limits, str):
        return [raw_limits]
    return []


def _extract_result_json(stdout: str) -> dict[str, Any] | None:
    marker = "DARTLAB_RESULT_JSON="
    for line in stdout.splitlines():
        if marker not in line:
            continue
        raw = line.split(marker, 1)[1].strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            try:
                import ast

                parsed = ast.literal_eval(raw)
            except (SyntaxError, ValueError):
                return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _first_numeric_key(rows: list[dict[str, Any]]) -> str | None:
    candidates: list[str] = []
    for row in rows:
        for key, value in row.items():
            if _is_identifier_or_rank_key(str(key)):
                continue
            if isinstance(value, (int, float)):
                candidates.append(str(key))
                continue
            try:
                float(str(value).replace(",", ""))
            except (TypeError, ValueError):
                continue
            candidates.append(str(key))
    if not candidates:
        return None
    return sorted(dict.fromkeys(candidates), key=_metric_key_score, reverse=True)[0]


def _table_metric_from_payload(rows: list[dict[str, Any]], payload: dict[str, Any], meta: dict[str, Any]) -> str | None:
    metric = payload.get("metric") or meta.get("metric")
    if isinstance(metric, str) and metric:
        return metric
    values = payload.get("values")
    if isinstance(values, dict):
        for key in values:
            if any(key in row for row in rows):
                return str(key)
    return _first_numeric_key(rows)


def _is_identifier_or_rank_key(key: str) -> bool:
    lowered = key.lower()
    identifier_tokens = ("code", "cd", "id", "corp", "isu", "ticker", "symbol", "rank", "순위", "코드")
    return any(token in lowered for token in identifier_tokens)


def _metric_key_score(key: str) -> int:
    lowered = key.lower()
    score = 0
    if any(token in lowered for token in ("return", "ret", "pct", "rate", "ratio", "fluc", "change", "수익률", "등락률", "비율")):
        score += 30
    if any(token in lowered for token in ("score", "value", "close", "price", "amount", "sales", "profit", "margin", "idx", "점수", "값", "종가", "가격", "이익", "매출")):
        score += 10
    if any(token in lowered for token in ("start", "begin", "end", "base", "기준", "시작", "종료")):
        score -= 3
    return score
