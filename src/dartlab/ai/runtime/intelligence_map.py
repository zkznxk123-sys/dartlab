"""Runtime Intelligence Map for the workspace-native AI agent.

The generated Intelligence Pack is the primary compact understanding surface.
When the pack is missing or stale, this module falls back to runtime inspection.
It is not a planner and does not own domain rules.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from dartlab.ai.runtime.intelligence_pack import loadIntelligencePack, packSummary, searchIntelligencePack

OFFICIAL_AGENT_TOOLS = (
    "workspace_status",
    "read_text",
    "inspect_data",
    "run_python",
    "search_workspace",
    "create_artifact",
    "finalize_answer",
)

ENGINE_LIBRARY_NAMES = (
    "Company",
    "gather",
    "scan",
    "macro",
    "industry",
    "analysis",
    "credit",
    "quant",
    "viz",
)


def buildIntelligenceMap(
    *,
    workspaceRoot: Path,
    dataRoot: Path,
    question: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Build a compact map over the official DartLab understanding surfaces."""
    pack = loadIntelligencePack()
    if pack.get("available"):
        graph = _graph_summary(question)
        data_catalog = list(pack.get("dataCatalog") or [])[: max(1, min(int(limit or 8), 20))]
        return _drop_empty(
            {
                "name": pack.get("name") or "DartLab Financial Workspace Agent",
                "loop": pack.get("loop") or ["observe", "inspect", "compute", "verify", "answer"],
                "pack": packSummary(pack),
                "officialAgentTools": pack.get("officialAgentTools") or list(OFFICIAL_AGENT_TOOLS),
                "engineLibraries": pack.get("engineLibraries") or list(ENGINE_LIBRARY_NAMES),
                "apiMap": list(pack.get("apiMap") or [])[:limit],
                "capabilitySkillMap": list(pack.get("capabilitySkillMap") or [])[:limit],
                "dataCatalog": data_catalog,
                "analysisGraph": graph,
                "processMap": _selected_processes(pack, graph, limit=limit),
                "recipeMap": pack.get("recipeMap"),
                "visualContract": pack.get("visualContract"),
                "safetyPolicy": pack.get("safetyPolicy"),
            }
        )
    graph = _graph_summary(question)
    return _drop_empty(
        {
            "name": "DartLab Financial Workspace Agent",
            "loop": ["observe", "inspect", "compute", "verify", "answer"],
            "officialAgentTools": list(OFFICIAL_AGENT_TOOLS),
            "engineLibraries": list(ENGINE_LIBRARY_NAMES),
            "apiMap": _api_map(limit=limit),
            "dataCatalog": buildDataCatalog(dataRoot=dataRoot, workspaceRoot=workspaceRoot, limit=limit),
            "analysisGraph": graph,
            "recipeMap": _recipe_map(graph),
        }
    )


def buildDataCatalog(*, dataRoot: Path, workspaceRoot: Path | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Return a bounded catalog of common local datasets without reading them."""
    limit = max(1, min(int(limit or 8), 20))
    roots = _candidate_data_roots(dataRoot)
    rows: list[dict[str, Any]] = []
    for root in roots:
        exists = root.exists()
        item: dict[str, Any] = {
            "id": _dataset_id(dataRoot, root),
            "path": _display_path(root, workspaceRoot),
            "exists": exists,
        }
        if exists and root.is_dir():
            files = _recent_data_files(root, limit=limit)
            item["fileCountSample"] = len(files)
            item["files"] = [
                {
                    "path": _display_path(path, workspaceRoot),
                    "format": path.suffix.lstrip("."),
                    "bytes": _safe_size(path),
                    "modified": _safe_mtime(path),
                }
                for path in files
            ]
        rows.append(_drop_empty(item))
    return rows


def searchIntelligenceMap(
    query: str,
    *,
    workspaceRoot: Path,
    dataRoot: Path,
    question: str | None = None,
    kind: str = "any",
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search the generated map before falling back to raw file search."""
    terms = _terms(query)
    if not terms:
        return []
    limit = max(1, min(int(limit or 10), 50))
    out = searchIntelligencePack(query, kind=kind, limit=limit)
    if len(out) >= limit:
        return out[:limit]

    rows = _index_map(buildIntelligenceMap(workspaceRoot=workspaceRoot, dataRoot=dataRoot, question=question, limit=8))
    seen = {str(row.get("path") or "") for row in out}
    for row in rows:
        if kind not in {"any", "capabilities"} and row.get("kind") not in {kind, f"intelligence.{kind}"}:
            continue
        if str(row.get("path") or "") in seen:
            continue
        haystack = " ".join(str(row.get(key) or "") for key in ("path", "kind", "summary", "detail")).lower()
        score = sum(1 for term in terms if term in haystack)
        if score <= 0:
            continue
        out.append({**row, "score": score + float(row.get("baseScore") or 0)})
    out.sort(key=lambda item: (-float(item.get("score") or 0), str(item.get("path") or "")))
    return out[:limit]


def dataProfileForFrame(frame: Any, *, path: str | None = None, latest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Infer semantic column roles for a Polars-like frame."""
    columns = [str(col) for col in getattr(frame, "columns", [])]
    dtypes = {str(name): str(dtype) for name, dtype in zip(columns, getattr(frame, "dtypes", []), strict=False)}
    roles = {col: _column_role(col, dtypes.get(col, "")) for col in columns}
    numeric_columns = [col for col, role in roles.items() if role == "metric"]
    date_columns = [col for col, role in roles.items() if role == "date"]
    entity_columns = [col for col, role in roles.items() if role in {"target", "identifier"}]
    metric_candidates = _rank_metric_candidates(numeric_columns)
    return _drop_empty(
        {
            "path": path,
            "rowCount": getattr(frame, "height", None),
            "columnRoles": roles,
            "dateColumns": date_columns,
            "targetColumns": entity_columns,
            "metricCandidates": metric_candidates,
            "latest": latest,
            "universe": _universe_hint(frame, entity_columns),
        }
    )


def _graph_summary(question: str | None) -> dict[str, Any]:
    try:
        from dartlab.core.analysisGraph import graphStatus, understandingPacketForQuestion

        status = graphStatus()
        packet = understandingPacketForQuestion(question or "")
    except Exception:  # noqa: BLE001
        return {"status": {"graphVersion": 0, "sourceHash": "unavailable"}}
    return _drop_empty(
        {
            "status": status,
            "understandingPacket": packet if question else None,
        }
    )


def _recipe_map(graph: dict[str, Any]) -> dict[str, Any]:
    packet = graph.get("understandingPacket") or {}
    process_maps = packet.get("processMaps") or []
    if not process_maps:
        return {"source": "generated_process_map", "candidates": []}
    return {
        "source": "generated_process_map",
        "candidates": [
            _drop_empty(
                {
                    "id": process.get("id"),
                    "questionType": process.get("questionType"),
                    "summary": process.get("summary"),
                    "requiredEvidence": process.get("requiredEvidence"),
                    "requiredArtifacts": process.get("requiredArtifacts"),
                    "requiredVisuals": process.get("requiredVisuals"),
                    "acceptanceCriteria": process.get("acceptanceCriteria"),
                }
            )
            for process in process_maps[:5]
            if isinstance(process, dict)
        ],
    }


def _selected_processes(pack: dict[str, Any], graph: dict[str, Any], *, limit: int) -> dict[str, Any]:
    packet = graph.get("understandingPacket") or {}
    selected_ids = list(packet.get("processMapIds") or [])[:limit]
    all_processes = pack.get("processMap") or {}
    if not selected_ids:
        return {}
    return {pid: all_processes.get(pid) for pid in selected_ids if all_processes.get(pid)}


def _api_map(*, limit: int) -> list[dict[str, Any]]:
    try:
        import dartlab
    except Exception:  # noqa: BLE001
        return []
    rows: list[dict[str, Any]] = []
    for name in sorted(getattr(dartlab, "__all__", [])):
        obj = getattr(dartlab, name, None)
        if obj is None:
            continue
        doc = inspect.getdoc(obj) or ""
        summary = doc.splitlines()[0] if doc else ""
        rows.append(
            {
                "name": f"dartlab.{name}",
                "kind": "class" if inspect.isclass(obj) else "function" if callable(obj) else "object",
                "summary": summary,
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _candidate_data_roots(dataRoot: Path) -> list[Path]:
    candidates = [
        dataRoot / "krx" / "indices",
        dataRoot / "krx" / "prices",
        dataRoot / "krx" / "ohlcv",
        dataRoot / "macro",
        dataRoot / "dart",
        dataRoot / "krxList",
    ]
    return list(dict.fromkeys(candidates))


def _recent_data_files(root: Path, *, limit: int) -> list[Path]:
    files: list[Path] = []
    for suffix in ("*.parquet", "*.csv", "*.tsv", "*.json"):
        try:
            files.extend(path for path in root.glob(suffix) if path.is_file())
        except OSError:
            continue
    files.sort(key=lambda item: (_safe_mtime(item) or "", item.name), reverse=True)
    return files[:limit]


def _dataset_id(dataRoot: Path, path: Path) -> str:
    try:
        rel = path.relative_to(dataRoot)
    except ValueError:
        rel = path
    return ".".join(part for part in rel.parts if part)


def _display_path(path: Path, workspaceRoot: Path | None) -> str:
    if workspaceRoot is not None:
        try:
            return str(path.relative_to(workspaceRoot))
        except ValueError:
            pass
    return str(path)


def _safe_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _safe_mtime(path: Path) -> str | None:
    try:
        from datetime import datetime

        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


def _index_map(map_data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        {
            "path": "intelligence://architecture",
            "kind": "intelligence.architecture",
            "summary": map_data.get("name"),
            "detail": " ".join(map_data.get("officialAgentTools") or []),
            "baseScore": 0.5,
        }
    ]
    for item in map_data.get("apiMap") or []:
        rows.append(
            {
                "path": f"intelligence://api/{item.get('name')}",
                "kind": "capability",
                "summary": item.get("summary") or item.get("name"),
                "detail": item.get("kind"),
                "baseScore": 0.4,
            }
        )
    for item in map_data.get("dataCatalog") or []:
        rows.append(
            {
                "path": item.get("path"),
                "kind": "data",
                "summary": item.get("id"),
                "detail": " ".join(str(file.get("path")) for file in item.get("files") or []),
                "baseScore": 0.4,
            }
        )
    graph = map_data.get("analysisGraph") or {}
    packet = graph.get("understandingPacket") or {}
    for process in packet.get("processMaps") or []:
        rows.append(
            {
                "path": f"intelligence://process/{process.get('id')}",
                "kind": "intelligence.process",
                "summary": process.get("summary") or process.get("questionType"),
                "detail": " ".join(str(v) for v in process.get("toolNames") or []),
                "baseScore": 0.6,
            }
        )
    for cid in packet.get("contractIds") or []:
        rows.append(
            {
                "path": f"intelligence://contract/{cid}",
                "kind": "intelligence.contract",
                "summary": cid,
                "detail": " ".join(str(v) for v in packet.get("candidateTools") or []),
                "baseScore": 0.5,
            }
        )
    return rows


def _terms(query: str) -> list[str]:
    import re

    q = (query or "").lower()
    aliases: list[str] = []
    if any(word in q for word in ("지수", "index", "indices", "kospi", "kosdaq")):
        aliases.extend(["indices", "index", "krx", "gather.krx.close"])
    if any(word in q for word in ("주가", "가격", "price", "close", "종목", "상승", "오른")):
        aliases.extend(["prices", "price", "close", "krx", "gather.krx.close"])
    if any(word in q for word in ("공시", "dart", "filing")):
        aliases.extend(["dart", "filing", "disclosure"])
    raw = re.split(r"[^0-9a-zA-Z가-힣_./-]+", q)
    return [term for term in dict.fromkeys([*raw, *aliases]) if len(term) >= 2]


def _column_role(name: str, dtype: str) -> str:
    lowered = name.lower()
    if lowered in {"date", "bas_dd", "asof", "as_of", "rcept_date", "observeddate"} or lowered.endswith("date"):
        return "date"
    if lowered in {"stockcode", "stock_code", "code", "corp_code", "isin", "ticker", "idx_cd"}:
        return "identifier"
    if lowered in {"corpname", "corp_name", "name", "idx_nm", "index_name", "target", "종목", "지수"}:
        return "target"
    if any(token in dtype.lower() for token in ("int", "float", "decimal")):
        return "metric"
    return "text"


def _rank_metric_candidates(columns: list[str]) -> list[str]:
    preferred = (
        "return",
        "ret",
        "pct",
        "rate",
        "close",
        "clsprc",
        "score",
        "value",
        "amount",
        "수익률",
        "등락률",
        "종가",
    )
    return sorted(
        columns,
        key=lambda col: (
            0 if any(token in col.lower() for token in preferred) else 1,
            col.lower(),
        ),
    )[:12]


def _universe_hint(frame: Any, entity_columns: list[str]) -> dict[str, Any] | None:
    if not entity_columns:
        return None
    col = entity_columns[0]
    try:
        unique_count = frame.select(col).n_unique()
    except Exception:  # noqa: BLE001
        unique_count = None
    return {"column": col, "uniqueCount": unique_count}


def _drop_empty(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}
