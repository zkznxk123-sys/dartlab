"""Workspace-native financial agent runtime.

This module is the LLM-facing analysis workspace for ``dartlab.ask``.  It does
not expose every DartLab engine function as a tool.  The model gets a small
set of workspace tools, then reads, inspects, computes, verifies, and finalizes
inside one request-scoped session.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Generator

from dartlab.ai.runtime.events import AnalysisEvent
from dartlab.ai.runtime.intelligence_map import (
    ENGINE_LIBRARY_NAMES,
    OFFICIAL_AGENT_TOOLS,
    buildDataCatalog,
    buildIntelligenceMap,
    dataProfileForFrame,
    searchIntelligenceMap,
)
from dartlab.ai.runtime.workspace_session import AgentSession, Execution, _json_safe
from dartlab.ai.runtime.workspace_verify import (
    finalizeAnswer as _finalize_answer,
)
from dartlab.ai.runtime.workspace_verify import (
    looksLikeComputeQuestion,
    looksLikeDataQuestion,
)
from dartlab.ai.runtime.workspace_visual import (
    autoVisualFromRows,
    isMeaningfulVisualSpec,
    requiresCsvArtifact,
    requiresVisualExplanation,
)
from dartlab.ai.tools import AITool, toolsToOpenAiSchemas

_MAX_ROUNDS = 14
_MAX_TEXT_CHARS = 60_000
_MAX_TOOL_RESULT_CHARS = 24_000
_DATE_COL_HINTS = {
    "date",
    "bas_dd",
    "asof",
    "as_of",
    "rcept_date",
    "enddate",
    "latestdate",
    "period",
}
_HIGH_MEMORY_PATTERNS = ("sections", "retrievalblocks", "contextslices", "rawsections")


def buildWorkspaceAgentSystemPrompt(*, question: str, stockCode: str | None = None, corpName: str | None = None) -> str:
    target = f"{corpName}({stockCode})" if corpName and stockCode else stockCode or "없음"
    return f"""\
너는 DartLab workspace 안에서 일하는 금융 분석 에이전트다.

핵심 규칙:
- 내부 엔진 함수명을 맞히는 챗봇처럼 행동하지 말고, workspace를 직접 관찰하고 계산하라.
- 기본 루프는 Observe → Inspect → Compute → Verify → Answer다.
- 답변 전 반드시 finalize_answer를 호출한다. finalize_answer가 실패하면 지적된 문제를 고쳐 다시 호출한다.
- 문서/소스/데이터가 필요하면 read_text, search_workspace, inspect_data를 먼저 쓴다.
- 계산형 질문은 run_python으로 직접 계산한다. 실행 실패 시 stderr를 읽고 재시도한다.
- currentDate와 데이터 기준일은 다르다. "오늘"은 currentDate에만 쓴다.
- 데이터 파일의 최신 날짜는 "데이터 기준일(asOf)" 또는 "최신 관측일"이라고 표현한다.
- 차트는 계산표에서만 만들고, category 2개 미만 또는 숫자값 2개 미만이면 만들지 않는다.
- 강세/상승/랭킹/순위/비교/시계열 질문은 재사용 가능한 CSV와 의미 있는 visual을 함께 만든다.
- sections/retrievalBlocks/contextSlices 같은 대량 본문 접근은 하지 않는다.

사용자 질문: {question}
분석 대상 힌트: {target}
"""


def runWorkspaceAgent(
    llm: Any,
    messages: list[dict[str, Any]],
    *,
    question: str,
    stockCode: str | None = None,
    workspace: Any | None = None,
) -> Generator[str | AnalysisEvent, None, None]:
    """Run the workspace-native agent loop."""
    if not getattr(llm, "supports_native_tools", False):
        raise RuntimeError("현재 provider는 workspace agent tool calling을 지원하지 않습니다.")

    session = AgentSession(question=question, workspaceRoot=_repo_root(), dataRoot=_data_root())
    tools = _workspace_tools(session)
    schemas = toolsToOpenAiSchemas(tools)
    by_name = {tool.name: tool for tool in tools}
    finalize_tool = [tool for tool in tools if tool.name == "finalize_answer"]
    finalize_schemas = toolsToOpenAiSchemas(finalize_tool)
    finalize_by_name = {tool.name: tool for tool in finalize_tool}
    finalized = False

    yield AnalysisEvent("observe", {"currentDate": session.currentDate, "workspaceRoot": str(session.workspaceRoot)})

    for round_idx in range(_MAX_ROUNDS):
        finalize_only = _ready_to_finalize(session)
        active_schemas = finalize_schemas if finalize_only else schemas
        active_by_name = finalize_by_name if finalize_only else by_name
        tool_choice = "any" if not finalized else "none"
        llm_start = time.perf_counter()
        response_iter = llm.stream_with_tools(messages, active_schemas, tool_choice=tool_choice)
        resp = None
        streamed_answer: list[str] = []
        for part in response_iter:
            if isinstance(part, str):
                streamed_answer.append(part)
                continue
            resp = part
        if workspace is not None:
            try:
                workspace.recordLlmRound(int((time.perf_counter() - llm_start) * 1000))
            except Exception:  # noqa: BLE001
                pass
        if resp is None:
            if streamed_answer:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "최종 텍스트를 직접 스트리밍하지 말고 workspace 도구로 관찰/계산/검산한 뒤 "
                            "finalize_answer를 호출하세요."
                        ),
                    }
                )
                continue
            raise RuntimeError("LLM provider returned no response")

        if getattr(resp, "tool_calls", None):
            messages.append(llm.format_assistant_tool_calls(resp.answer, resp.tool_calls))
            for call in resp.tool_calls:
                name = call.name
                args = dict(call.arguments or {})
                yield AnalysisEvent(
                    "tool_call",
                    {
                        "id": call.id,
                        "name": name,
                        "arguments": _compact_args(args),
                        "round": round_idx + 1,
                    },
                )
                start = time.perf_counter()
                try:
                    if name not in active_by_name:
                        raise ValueError(f"unknown workspace tool: {name}")
                    if workspace is not None:
                        try:
                            workspace.recordToolCall(name=name, arguments=args, round=round_idx + 1)
                        except Exception:  # noqa: BLE001
                            pass
                    result = active_by_name[name].handler(**args)
                    status = "ok"
                except Exception as exc:  # noqa: BLE001
                    result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                    status = "error"
                duration_ms = int((time.perf_counter() - start) * 1000)
                result_text = _tool_result_text(result)
                artifacts = _artifacts_from_tool_result(result)
                if workspace is not None:
                    try:
                        workspace.recordToolLatency(
                            name=name,
                            durationMs=duration_ms,
                            resultSizeBytes=len(result_text.encode("utf-8")),
                            round=round_idx + 1,
                        )
                        if name != "finalize_answer":
                            workspace.recordToolResult(
                                sourceTool=name,
                                arguments=args,
                                result=result,
                                artifacts=artifacts,
                            )
                    except Exception:  # noqa: BLE001
                        pass
                phase = _phase_for_tool(name)
                event_payload = {
                    "id": call.id,
                    "name": name,
                    "status": status,
                    "result": result_text,
                    "round": round_idx + 1,
                    "durationMs": duration_ms,
                    "artifacts": artifacts,
                }
                yield AnalysisEvent("tool_result", event_payload)
                yield AnalysisEvent(phase, {"tool": name, "status": status, "summary": _summary(result)})

                if name == "create_artifact" and isinstance(result, dict) and result.get("kind") == "visual":
                    spec = result.get("spec")
                    if isinstance(spec, dict):
                        yield AnalysisEvent(
                            "chart", {"charts": [spec], "visuals": [{"id": result.get("id"), "spec": spec}]}
                        )
                elif name == "create_artifact" and isinstance(result, dict) and isinstance(result.get("visual"), dict):
                    visual = result["visual"]
                    spec = visual.get("spec")
                    if isinstance(spec, dict):
                        yield AnalysisEvent("chart", {"charts": [spec], "visuals": [visual]})
                elif name == "create_artifact" and artifacts:
                    yield AnalysisEvent("artifact", {"artifacts": artifacts})

                if name == "finalize_answer":
                    verification = result if isinstance(result, dict) else {"ok": False, "issues": ["invalid_finalize"]}
                    yield AnalysisEvent("verify", verification)
                    if verification.get("ok"):
                        finalized = True
                        answer = str(verification.get("answer") or "")
                        session.finalAnswer = answer
                        if workspace is not None:
                            try:
                                _attach_session_to_workspace(workspace, session)
                                workspace.recordFinalAnswer(answer)
                                generated_visuals = workspace.ensureRequiredVisuals(answer=answer)
                                if generated_visuals:
                                    yield AnalysisEvent(
                                        "chart",
                                        {
                                            "charts": [item.spec for item in generated_visuals],
                                            "visuals": [item.toDict() for item in generated_visuals],
                                        },
                                    )
                            except Exception:  # noqa: BLE001
                                pass
                        yield answer
                        return

                messages.append(llm.format_tool_result(call.id, result_text))
            continue

        answer = str(getattr(resp, "answer", "") or "").strip()
        if answer and not finalized:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "최종 답변을 바로 쓰지 말고 workspace 도구로 관찰/계산/검산한 뒤 finalize_answer를 호출하세요."
                    ),
                }
            )
            continue

    session.verificationIssues.append("max_rounds_reached")
    session.add_limit("agent: max rounds reached before verified finalize")
    if workspace is not None:
        try:
            workspace.markMaxRoundsReached()
        except Exception:  # noqa: BLE001
            pass
    if workspace is not None:
        _attach_session_to_workspace(workspace, session)
    fallback = _fallback_answer(session)
    yield fallback


def _workspace_tools(session: AgentSession) -> list[AITool]:
    return [
        AITool(
            name="workspace_status",
            description=(
                "DartLab Financial Workspace Agent status, Intelligence Map, currentDate, "
                "data roots, engine libraries, and common data locations."
            ),
            parameters={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            handler=lambda: _workspace_status(session),
        ),
        AITool(
            name="read_text",
            description="Read UTF-8 text from ops/docs/source/docstring files inside the DartLab workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Workspace-relative or allowed absolute path."},
                    "max_chars": {"type": "integer", "minimum": 1, "maximum": 200000, "default": 60000},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=lambda path, max_chars=60000: _read_text(session, path, max_chars),
        ),
        AITool(
            name="inspect_data",
            description=(
                "Inspect parquet/csv schema, head, tail, latest observed date, row count, "
                "columns, and semantic data profile."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path_or_query": {"type": "string", "description": "Data file path or search query."},
                    "sample": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                    "columns": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["path_or_query"],
                "additionalProperties": False,
            },
            handler=lambda path_or_query, sample=5, columns=None: _inspect_data(
                session, path_or_query, sample, columns
            ),
        ),
        AITool(
            name="run_python",
            description="Run Python with dartlab and polars in the workspace root. Use for calculations and recovery.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to run. Print compact results."},
                    "timeout": {"type": "integer", "minimum": 5, "maximum": 120, "default": 60},
                },
                "required": ["code"],
                "additionalProperties": False,
            },
            handler=lambda code, timeout=60: _run_python(session, code, timeout),
        ),
        AITool(
            name="search_workspace",
            description="Search Intelligence Map first, then workspace files, docs, source paths, capabilities, and data filenames.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["any", "docs", "source", "data", "capabilities"],
                        "default": "any",
                    },
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            handler=lambda query, kind="any", limit=20: _search_workspace(session, query, kind, limit),
        ),
        AITool(
            name="create_artifact",
            description="Create reusable CSV/JSON/visual artifact from computed data. Visuals need 2+ categories and values.",
            parameters={
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["csv", "json", "visual"]},
                    "name": {"type": "string"},
                    "data": {
                        "description": "Rows/list/dict/string for csv/json, or chart spec for visual.",
                        "oneOf": [
                            {"type": "array", "items": {"type": "object", "additionalProperties": True}},
                            {"type": "object", "additionalProperties": True},
                            {"type": "string"},
                        ],
                    },
                },
                "required": ["kind", "data"],
                "additionalProperties": False,
            },
            handler=lambda kind, data, name="result": _create_artifact(session, kind, data, name),
        ),
        AITool(
            name="finalize_answer",
            description="Submit the final answer after observation, computation, and verification.",
            parameters={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "artifact_refs": {"type": "array", "items": {"type": "string"}},
                    "limits": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["answer"],
                "additionalProperties": False,
            },
            handler=lambda answer, evidence_refs=None, artifact_refs=None, limits=None: _finalize_answer(
                session,
                answer,
                evidence_refs or [],
                artifact_refs or [],
                limits or [],
            ),
        ),
    ]


def _workspace_status(session: AgentSession) -> dict[str, Any]:
    data_paths = _common_data_paths(session)
    intelligence = buildIntelligenceMap(
        workspaceRoot=session.workspaceRoot,
        dataRoot=session.dataRoot,
        question=session.question,
        limit=8,
    )
    result = {
        "agent": "DartLab Financial Workspace Agent",
        "currentDate": session.currentDate,
        "workspaceRoot": str(session.workspaceRoot),
        "dataRoot": str(session.dataRoot),
        "intelligenceMap": intelligence,
        "commonData": data_paths,
        "engineLibraries": list(ENGINE_LIBRARY_NAMES),
        "llmFacingTools": list(OFFICIAL_AGENT_TOOLS),
        "loop": ["observe", "inspect", "compute", "verify", "answer"],
        "rules": [
            "currentDate is not data asOf",
            "use inspect_data before data/date claims",
            "use run_python for calculations",
            "finalize_answer is required",
        ],
    }
    pack = intelligence.get("pack") or {}
    process_map = intelligence.get("processMap") or {}
    session.record_trace(
        "observe",
        {
            "tool": "workspace_status",
            "pack": pack,
            "processMapIds": list(process_map.keys()),
        },
    )
    return result


def _ready_to_finalize(session: AgentSession) -> bool:
    if looksLikeDataQuestion(session.question) and not session.observations:
        return False
    if looksLikeComputeQuestion(session.question) and not any(ex.ok for ex in session.executions):
        return False
    if requiresCsvArtifact(session.question) and not any(
        str(item.get("format") or "") == "csv" for item in session.artifacts
    ):
        return False
    if requiresVisualExplanation(session.question) and not session.visuals:
        return False
    if session.executions and session.executions[-1].returncode != 0:
        return False
    return bool(session.observations or session.executions or session.artifacts or session.visuals)


def _read_text(session: AgentSession, path: str, max_chars: int = 60_000) -> dict[str, Any]:
    p = _resolve_allowed_path(session, path)
    if p is None:
        return {"ok": False, "error": "path is outside allowed workspace/data roots", "path": path}
    lowered = str(p).lower()
    if any(pattern in lowered for pattern in _HIGH_MEMORY_PATTERNS):
        return {"ok": False, "error": "high-memory text path blocked", "path": str(p)}
    if not p.exists() or p.is_dir():
        return {"ok": False, "error": "file not found", "path": str(p)}
    data = p.read_text(encoding="utf-8", errors="replace")
    max_chars = max(1, min(int(max_chars or 60_000), 200_000))
    truncated = len(data) > max_chars
    text = data[:max_chars]
    session.record_trace("inspect", {"tool": "read_text", "path": str(p), "truncated": truncated})
    return {"ok": True, "path": str(p), "chars": len(data), "truncated": truncated, "text": text}


def _inspect_data(
    session: AgentSession,
    path_or_query: str,
    sample: int = 5,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    p = _resolve_data_path_or_query(session, path_or_query)
    if p is None:
        return {"ok": False, "error": "data file not found", "query": path_or_query}
    if not p.exists() or p.is_dir():
        return {"ok": False, "error": "data path is not a file", "path": str(p)}

    sample = max(1, min(int(sample or 5), 20))
    suffix = p.suffix.lower()
    if suffix not in {".parquet", ".csv", ".tsv"}:
        return {"ok": False, "error": "unsupported data format", "path": str(p)}

    import polars as pl

    if suffix == ".parquet":
        lazy = pl.scan_parquet(str(p))
        schema = lazy.collect_schema()
        all_columns = list(schema.names())
        selected = [c for c in columns or [] if c in all_columns] or all_columns
        frame = pl.read_parquet(p, columns=selected)
    else:
        separator = "\t" if suffix == ".tsv" else ","
        frame = pl.read_csv(p, separator=separator, infer_schema_length=1000)
        all_columns = list(frame.columns)
        selected = [c for c in columns or [] if c in all_columns]
        if selected:
            frame = frame.select(selected)

    latest = _latest_date_from_frame(frame)
    profile = dataProfileForFrame(frame, path=str(p), latest=latest)
    head = frame.head(sample).to_dicts()
    tail = frame.tail(sample).to_dicts()
    result = {
        "ok": True,
        "path": str(p),
        "format": suffix.lstrip("."),
        "rows": frame.height,
        "columns": list(frame.columns),
        "dtypes": {name: str(dtype) for name, dtype in zip(frame.columns, frame.dtypes, strict=True)},
        "latest": latest,
        "semanticProfile": profile,
        "head": _json_safe(head),
        "tail": _json_safe(tail),
    }
    if latest:
        session.add_observation(
            source=str(p),
            metric="latestObservedDate",
            value=latest.get("value"),
            observedDate=str(latest.get("value")),
            basis=f"max({latest.get('column')})",
            universe=profile.get("universe") or f"{frame.height} rows",
        )
    session.record_trace(
        "inspect",
        {
            "tool": "inspect_data",
            "path": str(p),
            "latest": latest,
            "semanticProfile": {
                "dateColumns": profile.get("dateColumns") or [],
                "targetColumns": profile.get("targetColumns") or [],
                "metricCandidates": profile.get("metricCandidates") or [],
            },
        },
    )
    return result


def _run_python(session: AgentSession, code: str, timeout: int = 60) -> dict[str, Any]:
    timeout = max(5, min(int(timeout or 60), 120))
    start = time.perf_counter()
    preamble = f"""\
from pathlib import Path
import os
WORKSPACE_ROOT = Path({str(session.workspaceRoot)!r})
DATA_ROOT = Path({str(session.dataRoot)!r})
os.chdir(WORKSPACE_ROOT)
import dartlab
dartlab.verbose = False
import polars as pl
pl.Config.set_tbl_rows(20)
pl.Config.set_tbl_cols(12)
pl.Config.set_tbl_width_chars(180)
"""
    full_code = preamble + "\n" + code
    with tempfile.TemporaryDirectory(prefix="dartlab_agent_") as tmp:
        script = Path(tmp) / "run.py"
        script.write_text(full_code, encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["DARTLAB_DATA_DIR"] = str(session.dataRoot)
        env["PYTHONPATH"] = os.pathsep.join([str(session.workspaceRoot / "src"), *sys.path])
        try:
            proc = subprocess.run(
                [_python_executable(), "-X", "utf8", str(script)],
                cwd=str(session.workspaceRoot),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=False,
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            returncode = proc.returncode
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\nTimeoutExpired: {timeout}s"
            returncode = 124
    duration_ms = int((time.perf_counter() - start) * 1000)
    execution = Execution(
        id=session.next_id("exec"),
        code=code,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        durationMs=duration_ms,
    )
    session.executions.append(execution)
    if returncode != 0:
        session.add_limit(f"execution failed: {execution.id}")
    else:
        session.limits = [limit for limit in session.limits if not limit.startswith("execution failed:")]
    _record_observations_from_stdout(session, execution)
    session.record_trace("compute", {"tool": "run_python", "executionId": execution.id, "ok": execution.ok})
    return execution.to_dict()


def _search_workspace(session: AgentSession, query: str, kind: str = "any", limit: int = 20) -> dict[str, Any]:
    limit = max(1, min(int(limit or 20), 50))
    map_rows = searchIntelligenceMap(
        query,
        workspaceRoot=session.workspaceRoot,
        dataRoot=session.dataRoot,
        question=session.question,
        kind=kind,
        limit=limit,
    )
    rows: list[dict[str, Any]] = list(map_rows)
    roots = _search_roots(session, kind)
    terms = _query_terms(query)
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(rows) >= limit * 4:
                break
            if path.is_dir():
                if any(pattern in str(path).lower() for pattern in _HIGH_MEMORY_PATTERNS):
                    continue
                continue
            rel = _safe_rel(path, session.workspaceRoot)
            hay = str(rel).lower()
            score = sum(1 for term in terms if term in hay)
            if score <= 0:
                continue
            rows.append(
                {
                    "path": str(rel),
                    "kind": _file_kind(path),
                    "score": score,
                    "bytes": path.stat().st_size if path.exists() else None,
                }
            )
    rows.sort(key=lambda row: (-int(row["score"]), str(row["path"])))
    if kind in {"any", "capabilities"}:
        rows.extend(_search_capabilities(query, limit=max(0, limit - len(rows))))
    out = rows[:limit]
    pack_hits = sum(1 for row in out if row.get("packSourceHash"))
    session.record_trace(
        "observe",
        {"tool": "search_workspace", "query": query, "results": len(out), "packHits": pack_hits},
    )
    return {"ok": True, "query": query, "results": out}


def _create_artifact(session: AgentSession, kind: str, data: Any, name: str = "result") -> dict[str, Any]:
    kind = str(kind or "").lower()
    name = _slug(name or "result")
    if kind == "visual":
        if not isinstance(data, dict):
            return {"ok": False, "kind": "visual", "error": "visual data must be a chart/diagram spec"}
        if not isMeaningfulVisualSpec(data):
            return {"ok": False, "kind": "visual", "error": "degenerate visual spec rejected"}
        item = {"id": session.next_id("viz"), "kind": "visual", "spec": _json_safe(data)}
        session.visuals.append(item)
        session.record_trace("compute", {"tool": "create_artifact", "kind": "visual", "id": item["id"]})
        return {"ok": True, **item}

    root = _artifact_root()
    day = date.today().isoformat()
    out_dir = root / day
    out_dir.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex[:12]
    suffix = "csv" if kind == "csv" else "json"
    path = out_dir / f"{name}_{token}.{suffix}"
    if kind == "csv":
        rows = _coerce_rows(data)
        if not rows:
            return {"ok": False, "kind": "csv", "error": "csv artifact requires rows"}
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        meta = {
            "id": path.stem,
            "kind": "table",
            "format": "csv",
            "primary": True,
            "mimeType": "text/csv; charset=utf-8",
            "label": name,
            "fileName": path.name,
            "day": day,
            "url": f"/api/ask/artifacts/{day}/{path.name}",
            "rows": len(rows),
            "columns": len(rows[0]),
        }
        auto_visual = autoVisualFromRows(session, rows, name)
    elif kind == "json":
        path.write_text(json.dumps(_json_safe(data), ensure_ascii=False, indent=2), encoding="utf-8")
        meta = {
            "id": path.stem,
            "kind": "json",
            "format": "json",
            "primary": False,
            "mimeType": "application/json; charset=utf-8",
            "label": name,
            "fileName": path.name,
            "day": day,
            "url": f"/api/ask/artifacts/{day}/{path.name}",
        }
        auto_visual = None
    else:
        return {"ok": False, "error": f"unsupported artifact kind: {kind}"}
    session.artifacts.append(meta)
    session.record_trace("compute", {"tool": "create_artifact", "kind": kind, "id": meta["id"]})
    result = {"ok": True, **meta}
    if auto_visual:
        result["visual"] = auto_visual
    return result


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _data_root() -> Path:
    try:
        from dartlab import config

        return Path(config.dataDir).resolve()
    except Exception:  # noqa: BLE001
        return (_repo_root() / "data").resolve()


def _artifact_root() -> Path:
    try:
        from dartlab import config

        return Path(config.dataDir) / "ai-artifacts"
    except Exception:  # noqa: BLE001
        return _repo_root() / "data" / "ai-artifacts"


def _python_executable() -> str:
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        for candidate in (Path(venv) / "Scripts" / "python.exe", Path(venv) / "bin" / "python"):
            if candidate.exists():
                return str(candidate)
    return sys.executable


def _resolve_allowed_path(session: AgentSession, path: str) -> Path | None:
    raw = Path(path)
    p = raw if raw.is_absolute() else session.workspaceRoot / raw
    try:
        resolved = p.resolve()
    except OSError:
        return None
    for root in (session.workspaceRoot.resolve(), session.dataRoot.resolve()):
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    return None


def _resolve_data_path_or_query(session: AgentSession, value: str) -> Path | None:
    p = _resolve_allowed_path(session, value)
    if p is not None and p.exists():
        return p
    results = _search_workspace(session, value, kind="data", limit=8).get("results") or []
    candidates: list[Path] = []
    for row in results:
        path = _resolve_allowed_path(session, str(row.get("path") or ""))
        if path is not None and path.suffix.lower() in {".parquet", ".csv", ".tsv"}:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda item: (_year_in_name(item.name), item.name), reverse=True)
    return candidates[0]


def _common_data_paths(session: AgentSession) -> list[dict[str, Any]]:
    return buildDataCatalog(dataRoot=session.dataRoot, workspaceRoot=session.workspaceRoot, limit=5)


def _search_roots(session: AgentSession, kind: str) -> list[Path]:
    if kind == "docs":
        return [session.workspaceRoot / "ops", session.workspaceRoot / "docs", session.workspaceRoot]
    if kind == "source":
        return [session.workspaceRoot / "src" / "dartlab"]
    if kind == "data":
        return [session.dataRoot]
    if kind == "capabilities":
        return []
    return [session.workspaceRoot / "ops", session.workspaceRoot / "src" / "dartlab", session.dataRoot]


def _query_terms(query: str) -> list[str]:
    q = query.lower()
    aliases = []
    if any(word in q for word in ("지수", "index", "indices", "kospi", "kosdaq")):
        aliases.extend(["indices", "index", "krx"])
    if any(word in q for word in ("주가", "가격", "price", "close", "종목")):
        aliases.extend(["prices", "price", "close", "krx"])
    if any(word in q for word in ("공시", "dart", "filing")):
        aliases.extend(["dart", "filing", "docs"])
    raw = re.split(r"[^0-9a-zA-Z가-힣_./-]+", q)
    return [term for term in dict.fromkeys([*raw, *aliases]) if len(term) >= 2]


def _search_capabilities(query: str, *, limit: int) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    try:
        from dartlab.core._capabilitySearch import searchCapabilities

        rows = searchCapabilities(query, topK=limit, minScore=0.25)
    except Exception:  # noqa: BLE001
        return []
    return [
        {
            "path": key,
            "kind": "capability",
            "score": round(float(score), 4),
            "summary": entry.get("summary") if isinstance(entry, dict) else None,
        }
        for key, entry, score in rows
    ]


def _latest_date_from_frame(frame: Any) -> dict[str, Any] | None:
    import polars as pl

    for col in frame.columns:
        normalized = str(col).lower()
        if normalized not in _DATE_COL_HINTS and "date" not in normalized and "dd" != normalized[-2:]:
            continue
        try:
            value = frame.select(pl.col(col).max()).item()
        except Exception:  # noqa: BLE001
            continue
        if value not in (None, ""):
            return {"column": col, "value": str(value)}
    return None


def _record_observations_from_stdout(session: AgentSession, execution: Execution) -> None:
    text = execution.stdout
    if not text:
        return
    for match in re.finditer(r"(20\d{2})[-./]?(\d{2})[-./]?(\d{2})", text):
        raw = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        session.add_observation(
            source=execution.id,
            metric="dateMention",
            value=raw,
            observedDate=raw,
            basis="run_python stdout",
        )
        break


def _coerce_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list) and data and all(isinstance(row, dict) for row in data):
        return [{str(k): _csv_scalar(v) for k, v in row.items()} for row in data]
    if isinstance(data, dict):
        rows = data.get("rows")
        if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
            return [{str(k): _csv_scalar(v) for k, v in row.items()} for row in rows]
    if isinstance(data, str):
        lines = [line for line in data.splitlines() if line.strip()]
        if not lines:
            return []
        delimiter = "\t" if "\t" in lines[0] else ","
        reader = csv.DictReader(lines, delimiter=delimiter)
        return [dict(row) for row in reader]
    return []


def _csv_scalar(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(_json_safe(value), ensure_ascii=False)


def _fallback_answer(session: AgentSession) -> str:
    parts = ["요청을 검증된 최종 답변으로 확정하지 못했습니다."]
    if session.limits:
        parts.append("한계: " + "; ".join(session.limits[:5]))
    if session.executions:
        last = session.executions[-1]
        parts.append(f"마지막 실행: {last.id}, returncode={last.returncode}")
    return "\n".join(parts)


def _attach_session_to_workspace(workspace: Any, session: AgentSession) -> None:
    try:
        workspace.coverage["workspaceAgent"] = session.response_meta()["agent"]
        existing_specs = {
            json.dumps(item.spec, ensure_ascii=False, sort_keys=True)
            for item in getattr(workspace, "visuals", [])
            if hasattr(item, "spec")
        }
        for visual in session.visuals:
            spec = visual.get("spec") if isinstance(visual, dict) else None
            if not isinstance(spec, dict):
                continue
            key = json.dumps(spec, ensure_ascii=False, sort_keys=True)
            if key in existing_specs:
                continue
            workspace.recordVisualSpec(
                spec,
                purpose=str(spec.get("purpose") or visual.get("purpose") or "explain"),
                evidenceIds=[],
            )
            existing_specs.add(key)
        for limit in session.limits:
            workspace.addLimit(limit)
    except Exception:  # noqa: BLE001
        return


def _phase_for_tool(name: str) -> str:
    if name in {"workspace_status", "search_workspace"}:
        return "observe"
    if name in {"read_text", "inspect_data"}:
        return "inspect"
    if name in {"run_python", "create_artifact"}:
        return "compute"
    if name == "finalize_answer":
        return "verify"
    return "observe"


def _tool_result_text(value: Any) -> str:
    text = json.dumps(_json_safe(value), ensure_ascii=False, indent=2, default=str)
    if len(text) > _MAX_TOOL_RESULT_CHARS:
        return text[:_MAX_TOOL_RESULT_CHARS] + f"\n... (+{len(text) - _MAX_TOOL_RESULT_CHARS} chars)"
    return text


def _artifacts_from_tool_result(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict) and value.get("ok") and value.get("url"):
        return [value]
    return []


def _summary(value: Any) -> str:
    if isinstance(value, dict):
        if value.get("error"):
            return str(value.get("error"))[:500]
        keys = [str(k) for k in value.keys() if k not in {"text", "head", "tail", "stdout"}]
        return ", ".join(keys[:12])
    return str(value)[:500]


def _safe_rel(path: Path, root: Path) -> Path:
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return path


def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".rst"}:
        return "docs"
    if suffix in {".py", ".ts", ".svelte", ".js"}:
        return "source"
    if suffix in {".parquet", ".csv", ".tsv", ".json"}:
        return "data"
    return "file"


def _year_in_name(name: str) -> int:
    match = re.search(r"(20\d{2})", name)
    return int(match.group(1)) if match else 0


def _compact_args(args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in args.items():
        if key == "code" and isinstance(value, str):
            out[key] = value[:1000] + ("..." if len(value) > 1000 else "")
        elif isinstance(value, str) and len(value) > 1000:
            out[key] = value[:1000] + "..."
        else:
            out[key] = value
    return _json_safe(out)


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")[:40] or "result"
