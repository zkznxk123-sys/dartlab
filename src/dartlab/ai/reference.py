"""Reference search and bounded context reading for Ask Workbench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import Ref, new_id
from .datasets import RuntimeDatasetCatalog

_TEXT_EXTS = {".md", ".py", ".toml", ".json", ".yaml", ".yml", ".txt"}


def search_reference(query: str, *, limit: int = 8) -> list[Ref]:
    """Reference 검색 — DartLab 문서·소스·데이터셋 context 찾기.

    Description
    -----------
    LLM 이 DartLab 사용법을 스스로 찾기 위한 짧은 resource-style snippet 을
    반환한다. 거대한 status dump 대신 workspace 문서, docstring, ops 문서,
    RuntimeDatasetCatalog 요약을 검색한다.

    Parameters
    ----------
    query : str
        검색 질의.
    limit : int, optional
        반환할 ref 최대 개수.

    Returns
    -------
    list[Ref]
        id : str — ref id
        kind : str — `"doc"`
        source : str — `search_reference` 또는 `RuntimeDatasetCatalog`
        payload : dict — resourceUri, title/path, snippet

    Raises
    ------
    없음
        읽을 수 없는 파일은 건너뛴다.

    Examples
    --------
    >>> search_reference("Company analysis", limit=2)
    [Ref(...), Ref(...)]

    Notes
    -----
    이 함수는 답변을 만들지 않는다. LLM 이 다음 action 을 선택할 context 만 준다.

    Guide
    -----
    capability/help 질문도 kernel 분기 없이 이 reference 를 통해 LLM 이 답한다.

    See Also
    --------
    read_context : 선택한 source window 를 읽는 action.
    """

    root = _repo_root()
    terms = [t.lower() for t in query.split() if len(t) >= 2]
    refs: list[Ref] = []

    if _prefer_skill_first(query, terms):
        refs.extend(_skill_refs(query, min(4, limit - len(refs))))
        if len(refs) >= limit:
            return refs[:limit]
        preferred_capabilities = _capability_ids_from_refs(refs)
        refs.extend(_capability_refs_for_ids(preferred_capabilities, min(2, limit - len(refs))))
        if len(refs) >= limit:
            return refs[:limit]

    refs.extend(_dataset_refs(terms, limit - len(refs)))
    if len(refs) >= limit:
        return refs[:limit]

    if not _prefer_skill_first(query, terms):
        refs.extend(_skill_refs(query, min(4, limit - len(refs))))
        if len(refs) >= limit:
            return refs[:limit]

        preferred_capabilities = _capability_ids_from_refs(refs)
        refs.extend(_capability_refs_for_ids(preferred_capabilities, min(2, limit - len(refs))))
        if len(refs) >= limit:
            return refs[:limit]

    refs.extend(_knowledge_refs(query, limit - len(refs)))
    if len(refs) >= limit:
        return refs[:limit]

    refs.extend(_capability_refs(query, terms, limit - len(refs)))
    if len(refs) >= limit:
        return refs[:limit]

    candidates = [root / "ops", root / "src" / "dartlab"]
    for candidate in candidates:
        if candidate.is_file():
            refs.extend(_search_file(candidate, terms, root=root, limit=limit - len(refs)))
        elif candidate.is_dir():
            for path in candidate.rglob("*"):
                if len(refs) >= limit:
                    return refs
                if path.is_file() and _is_searchable_reference_file(path, root):
                    refs.extend(_search_file(path, terms, root=root, limit=limit - len(refs)))
    return refs[:limit]


def _prefer_skill_first(query: str, terms: list[str]) -> bool:
    lowered = query.lower()
    markers = (
        "skill",
        "skills",
        "스킬",
        "스킬스",
        "capability",
        "사용법",
        "어떻게",
        "함수",
        "show",
        "뭐 할 수",
        "할 수 있어",
        "할수",
        "기능",
        "가능",
        "엔진",
        "조합",
        "응용",
    )
    return any(marker in lowered for marker in markers) or any(term in {"help", "usage"} for term in terms)


def _dataset_refs(terms: list[str], limit: int) -> list[Ref]:
    if limit <= 0:
        return []
    refs: list[Ref] = []
    locations = _rank_locations(RuntimeDatasetCatalog().list(), terms)
    if locations:
        refs.append(
            Ref(
                id=new_id("dataset"),
                kind="dataset",
                source="RuntimeDatasetCatalog",
                payload={
                    "resourceUri": "dartlab://datasets",
                    "title": "RuntimeDatasetCatalog",
                    "snippet": _catalog_snippet([location.to_dict() for location in locations[:20]]),
                },
            )
        )
        if len(refs) >= limit:
            return refs
    for location in locations:
        hay = " ".join([location.dataset_id, location.path, location.latest_as_of or ""]).lower()
        if not terms or any(term in hay for term in terms):
            refs.append(
                Ref(
                    id=new_id("dataset"),
                    kind="dataset",
                    source="RuntimeDatasetCatalog",
                    payload={
                        "resourceUri": f"dartlab://datasets/{location.dataset_id}",
                        "title": location.dataset_id,
                        "snippet": _dataset_snippet(location.to_dict()),
                    },
                )
            )
            if len(refs) >= limit:
                return refs
    return refs


def _capability_refs(query: str, terms: list[str], limit: int) -> list[Ref]:
    if limit <= 0:
        return []
    try:
        from dartlab.core._generated import CAPABILITIES
    except Exception:
        return []
    matches: list[tuple[float, str, dict[str, Any]]] = []
    for key, value in CAPABILITIES.items():
        if not isinstance(value, dict):
            continue
        hay = f"{key} " + " ".join(
            str(value.get(field) or "")
            for field in ("name", "summary", "guide", "returns", "requires", "example", "seeAlso", "questionTypes")
        )
        lowered = hay.lower()
        score = sum(2.0 if term in str(key).lower() else 1.0 for term in terms if term in lowered)
        if score > 0 or not terms:
            matches.append((score, str(key), value))
    refs: list[Ref] = []
    for score, key, value in sorted(matches, key=lambda item: (item[0], item[1]), reverse=True)[:limit]:
        refs.append(
            Ref(
                id=new_id("capability"),
                kind="capability",
                source="generatedCapabilities",
                payload={
                    "resourceUri": f"dartlab://capabilities/{key}",
                    "apiRef": key,
                    "score": score,
                    "summary": value.get("summary"),
                    "whenToUse": _line_limited_snippet(str(value.get("guide") or ""), max_lines=12, max_chars=900),
                    "parameters": value.get("args") or value.get("requiredInputs"),
                    "returns": _line_limited_snippet(
                        str(value.get("returns") or value.get("outputShape") or ""), max_lines=14, max_chars=1200
                    ),
                    "returnSchema": _compact_return_schema(value.get("returnSchema")),
                    "requires": value.get("requires"),
                    "examples": value.get("example"),
                    "requiredEvidence": value.get("requiredEvidence"),
                    "seeAlso": value.get("seeAlso"),
                },
            )
        )
    return refs


def _capability_refs_for_ids(capability_ids: list[str], limit: int) -> list[Ref]:
    if limit <= 0 or not capability_ids:
        return []
    try:
        from dartlab.core._generated import CAPABILITIES
    except Exception:
        return []
    refs: list[Ref] = []
    seen: set[str] = set()
    for key in capability_ids:
        if key in seen or key not in CAPABILITIES:
            continue
        seen.add(key)
        value = CAPABILITIES[key]
        if not isinstance(value, dict):
            continue
        refs.append(
            Ref(
                id=new_id("capability"),
                kind="capability",
                source="generatedCapabilities",
                payload={
                    "resourceUri": f"dartlab://capabilities/{key}",
                    "apiRef": key,
                    "score": "skillRef",
                    "summary": value.get("summary"),
                    "whenToUse": _line_limited_snippet(str(value.get("guide") or ""), max_lines=10, max_chars=800),
                    "parameters": value.get("args") or value.get("requiredInputs"),
                    "returns": _line_limited_snippet(
                        str(value.get("returns") or value.get("outputShape") or ""), max_lines=12, max_chars=1000
                    ),
                    "returnSchema": _compact_return_schema(value.get("returnSchema")),
                    "requires": value.get("requires"),
                    "examples": value.get("example"),
                    "requiredEvidence": value.get("requiredEvidence"),
                    "seeAlso": value.get("seeAlso"),
                },
            )
        )
        if len(refs) >= limit:
            break
    return refs


def _capability_ids_from_refs(refs: list[Ref]) -> list[str]:
    out: list[str] = []
    for ref in refs:
        if ref.kind != "skill":
            continue
        raw = ref.payload.get("capabilityRefs")
        if isinstance(raw, list):
            out.extend(str(item) for item in raw)
    return out


def _compact_return_schema(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "name": item.get("name"),
                "type": item.get("type"),
                "unit": item.get("unit"),
                "description": item.get("description"),
                "depth": item.get("depth", 0),
            }
        )
        if len(out) >= 20:
            break
    return out


def _skill_refs(query: str, limit: int) -> list[Ref]:
    if limit <= 0:
        return []
    try:
        from dartlab.skills import searchSkills

        matches = searchSkills(query, limit=limit)
    except Exception as exc:
        return [
            Ref(
                id=new_id("skill"),
                kind="skill",
                source="DartLabSkills",
                payload={"resourceUri": "dartlab://skills", "error": str(exc)},
            )
        ][:limit]
    refs: list[Ref] = []
    for match in matches:
        spec = match.skill
        refs.append(
            Ref(
                id=new_id("skill"),
                kind="skill",
                source="DartLabSkills",
                payload={
                    "resourceUri": f"dartlab://skills/{spec.id}",
                    "skillId": spec.id,
                    "title": spec.title,
                    "kind": spec.kind,
                    "scope": spec.scope,
                    "status": spec.status,
                    "category": spec.category,
                    "purpose": spec.purpose,
                    "whenToUse": spec.whenToUse,
                    "inputs": spec.inputs,
                    "outputs": spec.outputs,
                    "capabilityRefs": spec.capabilityRefs,
                    "datasetRefs": spec.datasetRefs,
                    "toolRefs": spec.toolRefs,
                    "knowledgeRefs": spec.knowledgeRefs,
                    "visualRefs": spec.visualRefs,
                    "procedure": spec.procedure[:8],
                    "requiredEvidence": spec.requiredEvidence,
                    "expectedOutputs": spec.expectedOutputs,
                    "visualGuidance": spec.visualGuidance[:4],
                    "failureModes": spec.failureModes[:6],
                    "runtimeCompatibility": spec.runtimeCompatibility,
                    "docs": spec.docs,
                    "quality": spec.quality,
                    "forbidden": spec.forbidden,
                    "skillSource": spec.source,
                    "score": match.score,
                    "reasons": match.reasons,
                },
            )
        )
    return refs


def _knowledge_refs(query: str, limit: int) -> list[Ref]:
    if limit <= 0:
        return []
    try:
        from dartlab.knowledge import searchKnowledge
    except Exception:
        return []
    return [
        Ref(
            id=new_id("knowledge"),
            kind="knowledge",
            source="DartLabKnowledge",
            payload={
                "resourceUri": f"dartlab://knowledge/{item.id}",
                "knowledgeId": item.id,
                "title": item.title,
                "summary": item.summary,
                "tags": item.tags,
                "source": item.source,
            },
        )
        for item in searchKnowledge(query, limit=limit)
    ]


def read_context(path: str, *, start_line: int = 1, max_chars: int = 4000) -> Ref:
    """Context 읽기 — workspace 텍스트 파일 일부를 ref 로 반환.

    Description
    -----------
    `search_reference()`가 찾은 source-addressed path 를 제한된 범위만 읽는다.
    workspace 밖 경로와 비텍스트 파일은 차단한다.

    Parameters
    ----------
    path : str
        workspace 내부 텍스트 파일 경로.
    start_line : int, optional
        1부터 시작하는 시작 줄 번호.
    max_chars : int, optional
        반환할 최대 문자 수.

    Returns
    -------
    Ref
        id : str — ref id
        kind : str — `"doc"`
        source : str — `"read_context"`
        payload : dict — path, startLine, text

    Raises
    ------
    ValueError
        workspace 밖 경로이거나 지원하지 않는 파일 형식.

    Examples
    --------
    >>> read_context("ops/skills.md", max_chars=1000)
    Ref(...)

    Notes
    -----
    대량 문서 덤프를 막기 위해 line window 와 max chars 를 강제한다.

    Guide
    -----
    검색 snippet 만으로 부족할 때 LLM 이 필요한 파일 조각만 읽는다.

    See Also
    --------
    search_reference : context 후보 검색.
    """

    root = _repo_root()
    target = (root / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if root not in [target, *target.parents]:
        raise ValueError("read_context path must stay inside workspace")
    if target.suffix.lower() not in _TEXT_EXTS:
        raise ValueError("read_context supports text source files only")
    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = max(1, int(start_line))
    buf: list[str] = []
    total = 0
    for idx, line in enumerate(lines[start - 1 :], start=start):
        item = f"{idx}: {line}"
        total += len(item) + 1
        if total > max_chars:
            break
        buf.append(item)
    return Ref(
        id=new_id("doc"),
        kind="doc",
        source="read_context",
        payload={"path": str(target.relative_to(root)), "startLine": start, "text": "\n".join(buf)},
    )


def _search_file(path: Path, terms: list[str], *, root: Path, limit: int) -> list[Ref]:
    if limit <= 0:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lower = text.lower()
    if terms and not any(term in lower for term in terms):
        return []
    pos = min([lower.find(term) for term in terms if term in lower] or [0])
    snippet = _line_limited_snippet(text[max(0, pos - 250) : pos + 1300].strip())
    return [
        Ref(
            id=new_id("doc"),
            kind="doc",
            source="search_reference",
            payload={
                "resourceUri": f"dartlab://workspace/{path.relative_to(root).as_posix()}",
                "path": str(path.relative_to(root)),
                "snippet": snippet,
            },
        )
    ]


def _dataset_snippet(data: dict[str, Any]) -> str:
    compact = {
        "datasetId": data.get("dataset_id"),
        "path": data.get("path"),
        "latestAsOf": data.get("latest_as_of"),
        "sampleFiles": data.get("files", [])[:5],
    }
    return _line_limited_snippet(json.dumps(compact, ensure_ascii=False, indent=2))


def _catalog_snippet(items: list[dict[str, Any]]) -> str:
    compact = [
        {
            "datasetId": item.get("dataset_id"),
            "path": item.get("path"),
            "latestAsOf": item.get("latest_as_of"),
        }
        for item in items
    ]
    return _line_limited_snippet(json.dumps({"datasets": compact}, ensure_ascii=False, indent=2))


def _rank_locations(locations: list[Any], terms: list[str]) -> list[Any]:
    def score(location: Any) -> tuple[int, str, str]:
        hay = " ".join([location.dataset_id, location.path, location.latest_as_of or ""]).lower()
        lexical = sum(1 for term in terms if term in hay)
        latest = location.latest_as_of or ""
        return (lexical, latest, location.dataset_id)

    return sorted(locations, key=score, reverse=True)


def _line_limited_snippet(text: str, *, max_lines: int = 40, max_chars: int = 2200) -> str:
    lines = text.splitlines()[:max_lines]
    snippet = "\n".join(lines)
    return snippet[:max_chars]


def _is_searchable_reference_file(path: Path, root: Path) -> bool:
    if path.suffix.lower() not in _TEXT_EXTS:
        return False
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        parts = path.parts
    blocked_parts = {"ai_backup", "__pycache__", ".git", ".venv", "server", "mcp"}
    if any(part in blocked_parts for part in parts):
        return False
    if len(parts) >= 3 and parts[0] == "src" and parts[1] == "dartlab" and parts[2] == "ai":
        return False
    return True


def _repo_root() -> Path:
    here = Path.cwd()
    for base in [here, *here.parents]:
        if (base / "pyproject.toml").exists() and (base / "src" / "dartlab").exists():
            return base
    return here


searchReference = search_reference
readContext = read_context
