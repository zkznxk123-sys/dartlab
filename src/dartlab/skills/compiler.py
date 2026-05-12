"""Skill catalog compiler for web search and runtime manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .registry import listSkills

_CATEGORY_META: dict[str, dict[str, str]] = {
    "start": {
        "title": "Start",
        "description": "설치, 첫 실행, skill catalog 사용법처럼 처음 진입할 때 필요한 절차.",
    },
    "runtime": {
        "title": "Runtime",
        "description": "Local Python, Pyodide, Web AI, MCP, VSCode 같은 실행 환경별 제약과 근거 흐름.",
    },
    "operation": {
        "title": "Operation",
        "description": "ops 원문을 skill 절차로 묶어 테스트, 문서, 릴리즈, 확장 규칙을 찾는 운영 지도.",
    },
    "engines": {
        "title": "Engines",
        "description": "엔진별 기본 사용법과 그 엔진이 소유한 응용 실행 스킬.",
    },
    "user": {
        "title": "User Skills",
        "description": "프로젝트 또는 사용자 확장 skill. 배포 산출물에는 기본 포함하지 않는다.",
    },
}
_CATEGORY_ORDER = (
    "start",
    "runtime",
    "operation",
    "engines",
    "user",
)


def buildSkillArtifacts(
    *,
    webDir: str | Path | None = None,
    includeUser: bool = False,
) -> dict[str, Any]:
    """Skill JSON 산출물 생성.

    Description
    -----------
    `dartlab.skills.specs` SkillSpec을 읽어 같은 package 안의 검색 JSON 과
    Pyodide compatibility manifest를 생성한다. 문서 SSOT는 생성 JSON 이 아니라
    `specs/**` SkillSpec 자체다. generated JSON 은 직접 수정하지 않는다.

    Parameters
    ----------
    webDir : str | Path | None, optional
        skill catalog 산출물 디렉터리. None이면 `src/dartlab/skills`.
    includeUser : bool, optional
        True면 project-local user skill까지 포함한다. 배포 산출물은 기본 False.

    Returns
    -------
    dict
        skillCount : int — 생성에 포함한 skill 수 (건)
        webDir : str — skill catalog 산출물 디렉터리
        categories : list[str] — 포함한 category 목록

    Raises
    ------
    ValueError
        SkillSpec lint 실패 또는 잘못된 capability ref.
    OSError
        산출물 쓰기 실패.

    Examples
    --------
    >>> buildSkillArtifacts(webDir="/tmp/web")["skillCount"] > 0
    True

    Notes
    -----
    `src/dartlab/skills/specs` 가 SkillSpec 원천이고, 같은 package의 JSON 은
    공개 catalog 산출물이다. 별도 root `skills/` 사본은 두지 않는다.

    Guide
    -----
    Web/runtime skill index 갱신 전 `uv run python -X utf8 scripts/build/generateSkills.py`
    로 재생성한다.

    See Also
    --------
    dartlab.skills.registry : SkillSpec 로딩과 lint.
    """

    skills = listSkills(includeUser=includeUser)
    web_path = Path(webDir) if webDir is not None else Path(__file__).resolve().parent
    _prepareGeneratedDir(web_path)

    categories = _orderedCategories({skill.category for skill in skills})
    search_index = [_searchDoc(skill) for skill in skills]
    meta = {
        "entrySkillId": "start.dartlabSkillOs",
        "canonicalSurface": "DartLab Skill OS",
        "skillCount": len(skills),
        "categories": [
            {
                "id": category,
                **_categoryMeta(category),
                "count": sum(1 for skill in skills if skill.category == category),
            }
            for category in categories
        ],
        "sourcePolicy": "Skills are public execution documents. API and behavior changes must update related skills.",
    }
    pyodide_manifest = [
        _pyodideDoc(skill) for skill in skills if _runtimeStatus(skill, "pyodide") in {"supported", "limited"}
    ]
    _writeJson(web_path / "index.json", {"meta": meta, "skills": search_index})
    _writeJson(web_path / "pyodide.json", {"skills": pyodide_manifest})
    _writeJson(web_path / "graph.json", _buildGraphPayload(skills))

    return {
        "skillCount": len(skills),
        "webDir": str(web_path),
        "categories": categories,
    }


def _buildGraphPayload(skills: list[Any]) -> dict[str, Any]:
    """SkillSpec 리스트 → graph.json 직렬화 payload.

    Description
    -----------
    buildSkillGraph 결과를 nodes + edges + cycles + entries + orphans +
    unreachable 6 필드 dict 로 직렬화. 랜딩 /skills/graph 라우트가 import.

    Parameters
    ----------
    skills : list[SkillSpec]
        listSkills() 결과.

    Returns
    -------
    dict
        nodes : list[dict] — id, title, category, purpose, inDegree, outDegree, cluster, isEntry, isLeaf, isOrphan, audiences
        edges : list[dict] — src, dst, kind
        entries : list[str]
        cycles : list[list[str]]
        orphans : list[str]
        unreachable : list[str]

    Raises
    ------
    없음
        검증/lint 는 graphLint.py.

    Examples
    --------
    >>> payload = _buildGraphPayload(listSkills())
    >>> 'nodes' in payload
    True

    Notes
    -----
    cluster 는 시각화 색상 그룹화 키. audiences 는 frontmatter directive 마커
    명시 주체 셋 (트랙 4 후 채워짐).

    Guide
    -----
    landing 빌드 시 import. 카테고리별 색상은 categoryColors SSOT.

    See Also
    --------
    dartlab.skills.graph.buildSkillGraph : 그래프 모델.
    """
    from dartlab.skills.graph import buildSkillGraph

    graph = buildSkillGraph(skills)
    return {
        "nodes": [
            {
                "id": node.id,
                "title": node.title,
                "category": node.category,
                "purpose": node.purpose,
                "inDegree": node.inDegree,
                "outDegree": node.outDegree,
                "cluster": node.cluster,
                "isEntry": node.isEntry,
                "isLeaf": node.isLeaf,
                "isOrphan": node.isOrphan,
                "audiences": list(node.audiences),
            }
            for node in graph.nodes
        ],
        "edges": [{"src": edge.src, "dst": edge.dst, "kind": edge.kind} for edge in graph.edges],
        "entries": list(graph.entryNodes),
        "cycles": [list(cycle) for cycle in graph.cycles],
        "orphans": list(graph.orphanNodes),
        "unreachable": list(graph.unreachableFromEntry),
    }


def _searchDoc(skill: Any) -> dict[str, Any]:
    from dartlab.skills.registry import _stepsFromRecipeBody

    # frontmatter recipeSteps 가 있으면 우선, 없으면 본문 ## 연계 절차 파싱 fallback.
    recipe_steps = (
        list(skill.recipeSteps) if skill.recipeSteps else _stepsFromRecipeBody(str(skill.source.get("body") or ""))
    )

    return {
        "id": skill.id,
        "title": _publicText(skill.title),
        "category": skill.category,
        "categoryTitle": _categoryMeta(skill.category)["title"],
        "kind": skill.kind,
        "status": skill.status,
        "purpose": _publicText(skill.purpose),
        "whenToUse": _publicList(skill.whenToUse),
        "inputs": _publicList(skill.inputs),
        "requiredInputs": _publicList(skill.requiredInputs),
        "outputs": _publicList(skill.outputs),
        "apiRefs": _publicList(skill.capabilityRefs),
        "toolRefs": _publicList(skill.toolRefs),
        "datasetRefs": _publicList(skill.datasetRefs),
        "knowledgeRefs": _publicList(skill.knowledgeRefs),
        "linkedSkills": _publicList(skill.linkedSkills),
        "requires": _publicList(skill.requires),
        "alternatives": _publicList(skill.alternatives),
        "succeededBy": _publicList(skill.succeededBy),
        "deprecatedBy": _publicList(skill.deprecatedBy),
        "sourceRefs": _publicList(skill.sourceRefs),
        "procedure": _publicList(skill.procedure),
        "recipeSteps": recipe_steps,
        "requiredEvidence": _publicList(skill.requiredEvidence),
        "expectedOutputs": _publicList(skill.expectedOutputs),
        "visualGuidance": _publicList(skill.visualGuidance),
        "failureModes": _publicList(skill.failureModes),
        "forbidden": _publicList(skill.forbidden),
        "examples": _publicList(skill.examples),
        "runtimeCompatibility": skill.runtimeCompatibility,
    }


def _pyodideDoc(skill: Any) -> dict[str, Any]:
    pyodide = skill.runtimeCompatibility.get("pyodide", {})
    return {
        "id": skill.id,
        "title": skill.title,
        "category": skill.category,
        "status": pyodide.get("status", "unknown"),
        "dataSources": pyodide.get("dataSources", []),
        "requiredSetup": pyodide.get("requiredSetup", []),
        "limitations": pyodide.get("limitations", []),
    }


def _runtimeStatus(skill: Any, runtime: str) -> str:
    value = skill.runtimeCompatibility.get(runtime, {})
    return str(value.get("status", "unknown")) if isinstance(value, dict) else "unknown"


def _publicList(values: list[Any]) -> list[str]:
    items: list[str] = []
    for value in values:
        text = _publicText(str(value))
        if text:
            items.append(text)
    return items


def _publicText(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    replacements = (
        ("docstring/generated capability", "엔진 기능 설명"),
        ("generated capability", "엔진 기능 설명"),
        ("capability-backed", "근거 기반"),
        ("skill/capability ref", "skill 문서"),
        ("capabilityRefs", "사용 기능"),
        ("capabilityRef", "사용 기능"),
        ("capability ref", "기능 참조"),
        ("capability view", "기능 설명"),
        ("capability schema", "API schema"),
        ("capability", "기능"),
    )
    for before, after in replacements:
        text = text.replace(before, after)
    return text


def _orderedCategories(categories: set[str]) -> list[str]:
    ordered = [category for category in _CATEGORY_ORDER if category in categories]
    ordered.extend(sorted(category for category in categories if category not in _CATEGORY_ORDER))
    return ordered


def _categoryMeta(category: str) -> dict[str, str]:
    return _CATEGORY_META.get(
        category,
        {
            "title": category,
            "description": f"{category} skill 목록.",
        },
    )


def _skillSourcePath(skill: Any) -> str:
    source = skill.source if isinstance(skill.source, dict) else {}
    path = source.get("path") or source.get("file")
    if path:
        return str(path).replace("\\", "/")
    return f"generated:{skill.id}"


def _writeJson(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepareGeneratedDir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in ("index.json", "pyodide.json"):
        target = path / file_name
        if target.exists():
            target.unlink()
