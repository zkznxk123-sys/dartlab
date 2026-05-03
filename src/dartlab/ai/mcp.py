"""Canonical MCP tool handlers backed by Ask Workbench."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .contracts import AnswerDraft, Ref, TraceEvent, WorkbenchTask
from .datasets import RuntimeDatasetCatalog, inspect_dataset, inspection_to_refs
from .kernel import _limits_from_execution, _refs_from_execution, create_task, runAsk
from .notebook import execution_to_ref, run_python
from .reference import read_context, search_reference
from .verify import verification_to_ref, verify_answer
from .visuals import compile_visual, visual_to_ref

CANONICAL_TOOL_NAMES = [
    "start_ask_session",
    "ask_kernel_status",
    "search_reference",
    "read_context",
    "inspect_dataset",
    "run_python",
    "compile_visual",
    "finalize_answer",
    "listDartlabSkills",
    "searchDartlabSkills",
    "explainDartlabSkill",
    "checkDartlabSkillEvidence",
]


@dataclass
class McpWorkbenchSession:
    task: WorkbenchTask
    refs: list[Ref] = field(default_factory=list)
    trace: list[TraceEvent] = field(default_factory=list)
    visuals: list[dict[str, Any]] = field(default_factory=list)
    limits: list[str] = field(default_factory=list)

    def add_ref(self, ref: Ref) -> Ref:
        self.refs.append(ref)
        return ref

    def add_event(self, kind: str, data: dict[str, Any]) -> TraceEvent:
        event = TraceEvent(kind=kind, data=data)
        self.trace.append(event)
        return event

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionId": self.task.id,
            "task": self.task.to_dict(),
            "refs": [ref.to_dict() for ref in self.refs],
            "trace": [event.to_dict() for event in self.trace],
            "visuals": self.visuals,
            "limits": self.limits,
        }


_SESSIONS: dict[str, McpWorkbenchSession] = {}


def tool_specs() -> list[dict[str, Any]]:
    """MCP tool spec 반환 — canonical Ask Workbench tools.

    Description
    -----------
    외부 MCP 클라이언트가 볼 기본 도구 목록을 반환한다. legacy engine tool 은
    기본 노출하지 않고 Ask Workbench action 만 노출한다.

    Parameters
    ----------
    없음
        인자를 받지 않는다.

    Returns
    -------
    list[dict]
        name : str — tool 이름
        description : str — tool 설명
        inputSchema : dict — JSON schema 형태 입력 스키마

    Raises
    ------
    없음
        정적 spec 생성은 예외를 던지지 않는다.

    Examples
    --------
    >>> [item["name"] for item in tool_specs()]
    ['start_ask_session', 'ask_kernel_status', ...]

    Notes
    -----
    MCP 는 AI 엔진 본체가 아니라 같은 workbench handler 의 transport 다.

    Guide
    -----
    새 도메인 기능은 MCP tool 을 늘리지 말고 DartLab public API/docstring 을
    개선한 뒤 `run_python`으로 사용하게 한다.

    See Also
    --------
    execute_tool : MCP tool 실행 handler.
    """

    return [
        {
            "name": "start_ask_session",
            "description": "Create an Ask Workbench task for a DartLab ask question.",
            "inputSchema": {"type": "object", "properties": {"question": {"type": "string"}}},
        },
        {
            "name": "ask_kernel_status",
            "description": "Return Ask Workbench Kernel status and runtime dataset roots.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "search_reference",
            "description": "Search DartLab Skill OS first, then capabilities, knowledge, docs, and runtime dataset catalog for short refs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sessionId": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
        },
        {
            "name": "read_context",
            "description": "Read a bounded source-addressed text window.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "max_chars": {"type": "integer"},
                    "sessionId": {"type": "string"},
                },
            },
        },
        {
            "name": "inspect_dataset",
            "description": "Inspect a runtime dataset id or parquet/csv path.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "sample": {"type": "integer"},
                    "sessionId": {"type": "string"},
                },
            },
        },
        {
            "name": "run_python",
            "description": "Run bounded Python code in the DartLab workspace.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "sessionId": {"type": "string"},
                },
            },
        },
        {
            "name": "compile_visual",
            "description": "Compile a validated chart spec from table rows.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "source_ref": {"type": "string"},
                    "rows": {"type": "array"},
                    "category": {"type": "string"},
                    "metric": {"type": "string"},
                    "sessionId": {"type": "string"},
                },
            },
        },
        {
            "name": "finalize_answer",
            "description": "Finalize a session answer through claim/ref verification.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sessionId": {"type": "string"},
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "evidence_refs": {"type": "array"},
                    "material_claims": {"type": "array"},
                    "visual_refs": {"type": "array"},
                    "limits": {"type": "array"},
                },
            },
        },
        {
            "name": "listDartlabSkills",
            "description": "List DartLab Skill OS entries for humans, internal AI, external AI, MCP, Web UI, and notebooks.",
            "inputSchema": {"type": "object", "properties": {"includeUser": {"type": "boolean"}}},
        },
        {
            "name": "searchDartlabSkills",
            "description": "Search DartLab Skill OS. Use this as the official route for analysis, engine, runtime, and operation procedures.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                    "includeUser": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "explainDartlabSkill",
            "description": "Return one DartLab Skill OS SkillSpec.",
            "inputSchema": {
                "type": "object",
                "properties": {"skillId": {"type": "string"}, "includeUser": {"type": "boolean"}},
                "required": ["skillId"],
            },
        },
        {
            "name": "checkDartlabSkillEvidence",
            "description": "Check whether refs satisfy a DartLab skill evidence contract.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skillId": {"type": "string"},
                    "refs": {"type": "array"},
                    "includeUser": {"type": "boolean"},
                },
                "required": ["skillId"],
            },
        },
    ]


def execute_tool(name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    """MCP tool 실행 — Ask Workbench handler 공유.

    Description
    -----------
    MCP transport 에서 들어온 tool 호출을 내부 workbench action 으로 연결한다.
    `/api/ask`와 별도 엔진을 만들지 않고 같은 Python handler 를 공유한다.

    Parameters
    ----------
    name : str
        실행할 MCP tool 이름.
    args : dict, optional
        tool 입력 인자.

    Returns
    -------
    dict
        tool 별 실행 결과. `inspect_dataset`은 DatasetInspection dict,
        `run_python`은 ExecutionResult dict, `compile_visual`은 VisualSpec dict.

    Raises
    ------
    ValueError
        알 수 없는 tool 이름.

    Examples
    --------
    >>> execute_tool("ask_kernel_status", {})["kernel"]
    'Ask Workbench Kernel'

    Notes
    -----
    `inspect_data`는 외부 호환 alias 로만 허용하고 기본 spec 에 노출하지 않는다.

    Guide
    -----
    외부 LLM 은 `search_reference -> inspect_dataset/run_python -> finalize_answer`
    흐름으로 DartLab 을 사용한다.

    See Also
    --------
    tool_specs : MCP 에 노출하는 canonical tool 목록.
    """

    args = args or {}
    if name == "start_ask_session":
        question = str(args.get("question") or "")
        task = create_task(question)
        session = McpWorkbenchSession(task=task)
        _SESSIONS[task.id] = session
        return session.to_dict()
    if name == "ask_kernel_status":
        catalog = RuntimeDatasetCatalog()
        return {
            "kernel": "Ask Workbench Kernel",
            "datasetRoots": [str(p) for p in catalog.roots],
            "datasets": [d.to_dict() for d in catalog.list()],
        }
    if name == "search_reference":
        session = _get_session(args)
        refs = search_reference(str(args.get("query") or ""), limit=int(args.get("limit") or 8))
        if session:
            for ref in refs:
                session.add_ref(ref)
            session.add_event("reference", {"refs": [ref.to_dict() for ref in refs]})
        return _with_session({"refs": [ref.to_dict() for ref in refs]}, session)
    if name == "read_context":
        session = _get_session(args)
        ref = read_context(
            str(args.get("path") or ""),
            start_line=int(args.get("start_line") or 1),
            max_chars=int(args.get("max_chars") or 4000),
        )
        if session:
            session.add_ref(ref)
            session.add_event("reference", {"ref": ref.to_dict()})
        return _with_session(ref.to_dict(), session)
    if name in {"inspect_dataset", "inspect_data"}:
        session = _get_session(args)
        inspection = inspect_dataset(str(args.get("target") or ""), sample=int(args.get("sample") or 5))
        refs = inspection_to_refs(inspection)
        if session:
            for ref in refs:
                session.add_ref(ref)
            session.add_event("inspect", {"result": inspection.to_dict(), "refs": [ref.to_dict() for ref in refs]})
        return _with_session(
            {"ok": inspection.ok, "inspection": inspection.to_dict(), "refs": [ref.to_dict() for ref in refs]}, session
        )
    if name == "run_python":
        session = _get_session(args)
        execution = run_python(str(args.get("code") or ""), timeout=int(args.get("timeout") or 60))
        execution_ref = execution_to_ref(execution)
        derived_refs = _refs_from_execution(execution, execution_ref.id)
        limits = _limits_from_execution(execution)
        if session:
            session.add_ref(execution_ref)
            for ref in derived_refs:
                session.add_ref(ref)
            session.limits.extend(limits)
            session.add_event(
                "execute",
                {
                    "refId": execution_ref.id,
                    "result": execution.to_dict(),
                    "derivedRefs": [ref.to_dict() for ref in derived_refs],
                },
            )
        return _with_session(
            {
                "execution": execution.to_dict(),
                "ref": execution_ref.to_dict(),
                "derivedRefs": [ref.to_dict() for ref in derived_refs],
                "limits": limits,
            },
            session,
        )
    if name == "compile_visual":
        session = _get_session(args)
        spec = compile_visual(
            source_ref=str(args.get("source_ref") or ""),
            rows=list(args.get("rows") or []),
            category=str(args.get("category") or ""),
            metric=str(args.get("metric") or ""),
            purpose=str(args.get("purpose") or "ranking"),
            title=args.get("title"),
            as_of=args.get("as_of"),
        )
        ref = visual_to_ref(spec)
        if session:
            session.visuals.append(spec.to_dict())
            session.add_ref(ref)
            session.add_event("visual", {"visual": spec.to_dict(), "refId": ref.id})
        return _with_session({"visual": spec.to_dict(), "ref": ref.to_dict()}, session)
    if name == "listDartlabSkills":
        from dartlab.skills import listSkills

        include_user = bool(args.get("includeUser", args.get("include_user", True)))
        return {"skills": [item.to_dict() for item in listSkills(includeUser=include_user)]}
    if name == "searchDartlabSkills":
        from dartlab.skills import searchSkills

        include_user = bool(args.get("includeUser", args.get("include_user", True)))
        return {
            "matches": [
                item.to_dict()
                for item in searchSkills(
                    str(args.get("query") or ""), limit=int(args.get("limit") or 8), includeUser=include_user
                )
            ]
        }
    if name == "explainDartlabSkill":
        from dartlab.skills import describeSkill

        include_user = bool(args.get("includeUser", args.get("include_user", True)))
        return describeSkill(str(args.get("skillId") or ""), includeUser=include_user)
    if name == "checkDartlabSkillEvidence":
        from dartlab.skills import checkEvidence

        include_user = bool(args.get("includeUser", args.get("include_user", True)))
        return checkEvidence(
            str(args.get("skillId") or ""), list(args.get("refs") or []), includeUser=include_user
        ).to_dict()
    if name == "inspect_visual":
        spec = args.get("spec") or {}
        categories = spec.get("categories") if isinstance(spec, dict) else None
        series = spec.get("series") if isinstance(spec, dict) else None
        return {
            "ok": isinstance(categories, list) and len(categories) >= 2 and isinstance(series, list) and bool(series)
        }
    if name == "finalize_answer":
        session = _get_session(args)
        if session:
            return _finalize_session(session, args)
        question = str(args.get("question") or "")
        return {"events": [event.to_dict() for event in runAsk(question)]}
    if name == "web_search":
        return {"ok": False, "error": "web_search is not enabled in local MCP v1"}
    if name == "write_artifact":
        return {"ok": False, "error": "write_artifact is optional and not enabled in kernel v1"}
    raise ValueError(f"unknown Ask Workbench MCP tool: {name}")


def _get_session(args: dict[str, Any]) -> McpWorkbenchSession | None:
    session_id = str(args.get("sessionId") or args.get("session_id") or "")
    if not session_id:
        return None
    session = _SESSIONS.get(session_id)
    if session is None:
        raise ValueError(f"unknown Ask Workbench session: {session_id}")
    return session


def _with_session(payload: dict[str, Any], session: McpWorkbenchSession | None) -> dict[str, Any]:
    if session is None:
        return payload
    payload["sessionId"] = session.task.id
    payload["refCount"] = len(session.refs)
    return payload


def _finalize_session(session: McpWorkbenchSession, args: dict[str, Any]) -> dict[str, Any]:
    answer = str(args.get("answer") or "")
    evidence_refs = [str(item) for item in args.get("evidence_refs") or args.get("evidenceRefs") or []]
    if not evidence_refs:
        evidence_refs = [ref.id for ref in session.refs if ref.kind != "verify"]
    visual_refs = [str(item) for item in args.get("visual_refs") or args.get("visualRefs") or []]
    if not visual_refs:
        visual_refs = [ref.id for ref in session.refs if ref.kind == "visual"]
    claims = args.get("material_claims") or args.get("materialClaims") or []
    limits = args.get("limits") or []
    draft = AnswerDraft(
        answer=answer,
        evidence_refs=evidence_refs,
        material_claims=[item for item in claims if isinstance(item, dict)] if isinstance(claims, list) else [],
        visual_refs=visual_refs,
        limits=session.limits + ([str(item) for item in limits] if isinstance(limits, list) else [str(limits)]),
    )
    verification = verify_answer(session.task, session.refs, draft)
    verify_ref = verification_to_ref(verification)
    session.add_ref(verify_ref)
    session.add_event("verify", {"refId": verify_ref.id, "result": verification.to_dict()})
    return {
        "ok": verification.ok,
        "answer": answer if verification.ok else "",
        "verification": verification.to_dict(),
        "verifyRef": verify_ref.to_dict(),
        "session": session.to_dict(),
    }
