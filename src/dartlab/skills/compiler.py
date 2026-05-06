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
    _prepare_generated_dir(web_path)

    categories = _ordered_categories({skill.category for skill in skills})
    search_index = [_search_doc(skill) for skill in skills]
    meta = {
        "entrySkillId": "start.dartlabSkillOs",
        "canonicalSurface": "DartLab Skill OS",
        "skillCount": len(skills),
        "categories": [
            {
                "id": category,
                **_category_meta(category),
                "count": sum(1 for skill in skills if skill.category == category),
            }
            for category in categories
        ],
        "sourcePolicy": "Skills are public execution documents. API and behavior changes must update related skills.",
    }
    pyodide_manifest = [
        _pyodide_doc(skill) for skill in skills if _runtime_status(skill, "pyodide") in {"supported", "limited"}
    ]
    _write_json(web_path / "index.json", {"meta": meta, "skills": search_index})
    _write_json(web_path / "pyodide.json", {"skills": pyodide_manifest})

    return {
        "skillCount": len(skills),
        "webDir": str(web_path),
        "categories": categories,
    }


def _search_doc(skill: Any) -> dict[str, Any]:
    from dartlab.skills.registry import _steps_from_recipe_body

    # frontmatter recipeSteps 가 있으면 우선, 없으면 본문 ## 연계 절차 파싱 fallback.
    recipe_steps = (
        list(skill.recipeSteps) if skill.recipeSteps else _steps_from_recipe_body(str(skill.source.get("body") or ""))
    )

    return {
        "id": skill.id,
        "title": _public_text(skill.title),
        "category": skill.category,
        "categoryTitle": _category_meta(skill.category)["title"],
        "kind": skill.kind,
        "status": skill.status,
        "purpose": _public_text(skill.purpose),
        "whenToUse": _public_list(skill.whenToUse),
        "inputs": _public_list(skill.inputs),
        "requiredInputs": _public_list(skill.requiredInputs),
        "outputs": _public_list(skill.outputs),
        "apiRefs": _public_list(skill.capabilityRefs),
        "toolRefs": _public_list(skill.toolRefs),
        "datasetRefs": _public_list(skill.datasetRefs),
        "knowledgeRefs": _public_list(skill.knowledgeRefs),
        "linkedSkills": _public_list(skill.linkedSkills),
        "requires": _public_list(skill.requires),
        "alternatives": _public_list(skill.alternatives),
        "succeededBy": _public_list(skill.succeededBy),
        "deprecatedBy": _public_list(skill.deprecatedBy),
        "sourceRefs": _public_list(skill.sourceRefs),
        "procedure": _public_list(skill.procedure),
        "recipeSteps": recipe_steps,
        "requiredEvidence": _public_list(skill.requiredEvidence),
        "expectedOutputs": _public_list(skill.expectedOutputs),
        "visualGuidance": _public_list(skill.visualGuidance),
        "failureModes": _public_list(skill.failureModes),
        "forbidden": _public_list(skill.forbidden),
        "examples": _public_list(skill.examples),
        "runtimeCompatibility": skill.runtimeCompatibility,
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


def _public_list(values: list[Any]) -> list[str]:
    items: list[str] = []
    for value in values:
        text = _public_text(str(value))
        if text:
            items.append(text)
    return items


def _public_text(value: str) -> str:
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


def _skill_source_path(skill: Any) -> str:
    source = skill.source if isinstance(skill.source, dict) else {}
    path = source.get("path") or source.get("file")
    if path:
        return str(path).replace("\\", "/")
    return f"generated:{skill.id}"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_generated_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for file_name in ("index.json", "pyodide.json"):
        target = path / file_name
        if target.exists():
            target.unlink()
