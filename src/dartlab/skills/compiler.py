"""Skill catalog compiler for docs, web search, and runtime manifests."""

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
    "engines": {
        "title": "Engines",
        "description": "DartLab 엔진을 어떤 목적에 연결할지 알려주는 사용 지도.",
    },
    "screens": {
        "title": "Screens",
        "description": "scan/gather 기반 후보 발굴, 횡단 비교, 시장 필터링 절차.",
    },
    "finance": {
        "title": "Finance",
        "description": "기업 분석, 공시 이벤트, 신용, 밸류에이션, 현금흐름 등 금융 리서치 절차.",
    },
    "visuals": {
        "title": "Visuals",
        "description": "표 근거가 있는 차트와 시각 산출물을 만들고 검증하는 절차.",
    },
    "basic": {
        "title": "Basic Engine Maps",
        "description": "공개 docstring/capability에서 자동 생성한 엔진별 능력 지도.",
    },
    "capability": {
        "title": "Capability Reference",
        "description": "공개 API docstring에서 자동 생성한 capability 검색 진입점.",
    },
    "user": {
        "title": "User Skills",
        "description": "프로젝트 또는 사용자 확장 skill. 배포 산출물에는 기본 포함하지 않는다.",
    },
}
_CATEGORY_ORDER = ("start", "runtime", "engines", "screens", "finance", "visuals", "basic", "capability", "user")


def buildSkillArtifacts(
    *,
    docsDir: str | Path = "docs/skills",
    webDir: str | Path = "landing/static/skills",
    includeUser: bool = False,
) -> dict[str, Any]:
    """Skill 산출물 생성 — docs와 web search index를 같은 원천에서 만든다.

    Description
    -----------
    `src/dartlab/skills` SkillSpec을 읽어 GitHub Pages용 Markdown, landing/Web
    검색 JSON, Pyodide compatibility manifest를 생성한다. 산출물은 직접 수정
    대상이 아니며 skill source와 docstring/capabilities에서 재생성한다.

    Parameters
    ----------
    docsDir : str | Path, optional
        생성할 공개 문서 디렉터리.
    webDir : str | Path, optional
        landing static 검색 index 디렉터리.
    includeUser : bool, optional
        True면 project-local user skill까지 포함한다. 배포 산출물은 기본 False.

    Returns
    -------
    dict
        skillCount : int — 생성에 포함한 skill 수 (건)
        docsDir : str — 문서 산출물 디렉터리
        webDir : str — web index 산출물 디렉터리
        categories : list[str] — 렌더링한 category 목록

    Raises
    ------
    ValueError
        SkillSpec lint 실패 또는 잘못된 capability ref.
    OSError
        산출물 쓰기 실패.

    Examples
    --------
    >>> buildSkillArtifacts(docsDir="/tmp/docs", webDir="/tmp/web")["skillCount"] > 0
    True

    Notes
    -----
    docs는 SSOT가 아니다. SkillSpec에서 렌더링되는 결과물이다.

    Guide
    -----
    GitHub Pages 갱신 전 `uv run python -X utf8 scripts/build/generateSkills.py`
    로 재생성한다.

    See Also
    --------
    dartlab.skills.registry : SkillSpec 로딩과 lint.
    """

    skills = listSkills(includeUser=includeUser)
    docs_path = Path(docsDir)
    web_path = Path(webDir)
    docs_path.mkdir(parents=True, exist_ok=True)
    web_path.mkdir(parents=True, exist_ok=True)

    categories = _ordered_categories({skill.category for skill in skills})
    _write_text(docs_path / "index.md", _render_index(skills, categories))
    _write_text(docs_path / "pyodide.md", _render_pyodide(skills))
    for category in categories:
        category_skills = [skill for skill in skills if skill.category == category]
        _write_text(docs_path / f"{category}.md", _render_category(category, category_skills))
        category_dir = docs_path / category
        category_dir.mkdir(parents=True, exist_ok=True)
        for skill in category_skills:
            _write_text(category_dir / f"{_slug(skill.id)}.md", _render_skill(skill))

    search_index = [_search_doc(skill) for skill in skills]
    pyodide_manifest = [
        _pyodide_doc(skill) for skill in skills if _runtime_status(skill, "pyodide") in {"supported", "limited"}
    ]
    _write_json(web_path / "index.json", {"skills": search_index})
    _write_json(web_path / "pyodide.json", {"skills": pyodide_manifest})

    return {
        "skillCount": len(skills),
        "docsDir": str(docs_path),
        "webDir": str(web_path),
        "categories": categories,
    }


def _render_index(skills: list[Any], categories: list[str]) -> str:
    lines = [
        "---",
        "title: DartLab Skills",
        "description: DartLab의 모든 분석 절차와 AI/MCP/Web 실행 흐름은 SkillSpec에서 생성되는 Skill Docs를 기준으로 한다.",
        "---",
        "",
        "# DartLab Skills",
        "",
        "이 문서는 `src/dartlab/skills` SkillSpec에서 생성된다. 직접 수정하지 않는다. 사람, 자체 AI, 외부 AI, MCP, Web UI는 같은 skill resolver와 같은 capability ref를 본다.",
        "",
        "## 사용 원칙",
        "",
        "- 분석 절차는 먼저 skill을 검색한다.",
        "- 선택한 skill의 `capabilityRefs`로 공개 API docstring/capability를 확인한다.",
        "- 실행 가능 범위는 `runtimeCompatibility`로 확인한다.",
        "- 결과는 table/value/date/visual 같은 근거 ref로 남긴 뒤 최종 답변 전에 검산한다.",
        "",
        "## 카테고리",
        "",
    ]
    counts = {category: sum(1 for skill in skills if skill.category == category) for category in categories}
    for category in categories:
        meta = _category_meta(category)
        lines.append(f"- [{meta['title']}]({category}) — {counts[category]}개: {meta['description']}")
    lines.extend(["", "## Runtime 특화 목록", "", "- [Pyodide 가능 skill 목록](pyodide)"])
    return "\n".join(lines) + "\n"


def _render_pyodide(skills: list[Any]) -> str:
    rows = [skill for skill in skills if _runtime_status(skill, "pyodide") in {"supported", "limited"}]
    lines = [
        "---",
        "title: DartLab Skills / Pyodide",
        "---",
        "",
        "# Pyodide 가능 Skill",
        "",
        "브라우저에서 바로 가능하거나 제한 조건에서 가능한 skill 목록이다. live API 최신성이 아니라 사용한 snapshot의 asOf 기준으로 판단한다.",
        "",
        "| skill | category | status | data sources |",
        "|---|---|---:|---|",
    ]
    for skill in sorted(rows, key=lambda item: (item.category, item.id)):
        pyodide = skill.runtimeCompatibility.get("pyodide", {})
        sources = pyodide.get("dataSources", []) if isinstance(pyodide, dict) else []
        source_text = "; ".join(str(item) for item in sources[:3])
        lines.append(
            f"| [{_md_text(skill.id)}]({skill.category}/{_slug(skill.id)}) | "
            f"`{_md_text(skill.category)}` | `{_md_text(_runtime_status(skill, 'pyodide'))}` | {_md_text(source_text)} |"
        )
    return "\n".join(lines) + "\n"


def _render_category(category: str, skills: list[Any]) -> str:
    meta = _category_meta(category)
    lines = [
        "---",
        f"title: DartLab Skills / {meta['title']}",
        f"description: {meta['description']}",
        "---",
        "",
        f"# {meta['title']}",
        "",
        meta["description"],
        "",
    ]
    for skill in sorted(skills, key=lambda item: item.id):
        lines.append(f"## [{skill.title}]({category}/{_slug(skill.id)})")
        lines.append("")
        lines.append(_md_text(skill.purpose))
        lines.append("")
        lines.append(f"- id: `{skill.id}`")
        lines.append(f"- status: `{skill.status}`")
        lines.append(f"- pyodide: `{_runtime_status(skill, 'pyodide')}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def _render_skill(skill: Any) -> str:
    body = skill.source.get("body") if isinstance(skill.source, dict) else ""
    lines = [
        "---",
        f"title: {skill.title}",
        f"skillId: {skill.id}",
        f"category: {skill.category}",
        "---",
        "",
        f"# {skill.title}",
        "",
        _md_text(skill.purpose),
        "",
        "## Metadata",
        "",
        f"- id: `{skill.id}`",
        f"- category: `{skill.category}`",
        f"- kind: `{skill.kind}`",
        f"- status: `{skill.status}`",
        f"- Pyodide: `{_runtime_status(skill, 'pyodide')}`",
        "",
    ]
    lines.extend(_list_section("When To Use", skill.whenToUse))
    lines.extend(_list_section("Capability Refs", [f"`{item}`" for item in skill.capabilityRefs]))
    lines.extend(_list_section("Dataset Refs", skill.datasetRefs))
    lines.extend(_list_section("Required Evidence", skill.requiredEvidence))
    lines.extend(_list_section("Expected Outputs", skill.expectedOutputs))
    lines.extend(_runtime_section(skill.runtimeCompatibility))
    if body:
        lines.extend(["## Guide", "", _md_text(body), ""])
    else:
        lines.extend(_list_section("Procedure", skill.procedure))
    lines.extend(_list_section("Forbidden", skill.forbidden))
    return "\n".join(lines) + "\n"


def _list_section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    lines = [f"## {title}", ""]
    for item in items:
        lines.append(f"- {_md_text(str(item))}")
    lines.append("")
    return lines


def _runtime_section(runtime: dict[str, Any]) -> list[str]:
    if not runtime:
        return []
    lines = ["## Runtime Compatibility", "", "| runtime | status | notes |", "|---|---:|---|"]
    for key, value in runtime.items():
        if not isinstance(value, dict):
            continue
        notes = value.get("notes") or value.get("limitations") or value.get("dataSources") or []
        if isinstance(notes, str):
            note_text = notes
        else:
            note_text = "; ".join(str(item) for item in notes[:3])
        lines.append(
            f"| `{_md_text(str(key))}` | `{_md_text(str(value.get('status', 'unknown')))}` | {_md_text(note_text)} |"
        )
    lines.append("")
    return lines


def _search_doc(skill: Any) -> dict[str, Any]:
    return {
        "id": skill.id,
        "title": skill.title,
        "category": skill.category,
        "categoryTitle": _category_meta(skill.category)["title"],
        "status": skill.status,
        "purpose": skill.purpose,
        "whenToUse": skill.whenToUse,
        "capabilityRefs": skill.capabilityRefs,
        "datasetRefs": skill.datasetRefs,
        "runtimeCompatibility": skill.runtimeCompatibility,
        "url": f"/docs/skills/{skill.category}/{_slug(skill.id)}",
    }


def _pyodide_doc(skill: Any) -> dict[str, Any]:
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


def _runtime_status(skill: Any, runtime: str) -> str:
    value = skill.runtimeCompatibility.get(runtime, {})
    return str(value.get("status", "unknown")) if isinstance(value, dict) else "unknown"


def _slug(value: str) -> str:
    return value.replace(":", "-").replace(".", "-")


def _ordered_categories(categories: set[str]) -> list[str]:
    ordered = [category for category in _CATEGORY_ORDER if category in categories]
    ordered.extend(sorted(category for category in categories if category not in _CATEGORY_ORDER))
    return ordered


def _category_meta(category: str) -> dict[str, str]:
    return _CATEGORY_META.get(
        category,
        {
            "title": category,
            "description": f"{category} skill 목록.",
        },
    )


def _md_text(value: str) -> str:
    return value.replace("{", "[").replace("}", "]")


def _write_text(path: Path, text: str) -> None:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).rstrip() + "\n"
    path.write_text(normalized, encoding="utf-8")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
