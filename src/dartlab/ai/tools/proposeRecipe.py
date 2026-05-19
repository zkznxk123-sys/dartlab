"""ProposeRecipe — recipe markdown spec 1 건 신규 작성 (chat-native).

`feedback_no_graph_regression.md` 준수: 자기개선 사다리 / HARVEST 자동 호출 도입 X. AI 가
사용자 질문에 자율적으로 호출하는 stateless 도구. 작성된 spec 의 status 는 항상 `drafted` —
승격은 운영자 CLI (`src/dartlab/skills/recipePromote.py`) 단독 권한.

작성 위치: `src/dartlab/skills/specs/recipes/{persona}[/{domain}...]/{slug}.md`.
id 는 `recipes.<persona>[.<domain>...].<slug>` 형식 (≥3 parts, depth 가변). recipe-전용
frontmatter (gap/falsifier/expectedNovelty/testUniverse) 강제. 동일 id 가 이미 있으면 거부.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dartlab.ai.contracts import Ref

from .types import ToolResult

_RECIPE_DIR = Path(__file__).resolve().parents[2] / "skills" / "specs" / "recipes"


def _validateGap(gap: Any) -> str | None:
    if not isinstance(gap, dict):
        return "gap 은 dict (예: {primary: [credit, macro]})"
    primary = gap.get("primary")
    if not isinstance(primary, list) or len(primary) < 2:
        return f"gap.primary 는 ≥2 개 엔진 이름 (got {primary!r})"
    if not all(isinstance(p, str) and p.strip() for p in primary):
        return "gap.primary 항목은 모두 비어있지 않은 문자열"
    return None


def _validateFalsifier(falsifier: Any) -> str | None:
    if not isinstance(falsifier, dict):
        return "falsifier 는 dict (description + pythonCheck)"
    desc = falsifier.get("description")
    if not isinstance(desc, str) or not desc.strip():
        return "falsifier.description 은 비어있지 않은 문자열"
    return None


def _slug(skillId: str) -> str:
    return skillId.split(".")[-1] or skillId


def _recipePath(skillId: str) -> Path:
    parts = skillId.split(".")
    if len(parts) >= 3 and parts[0] == "recipes":
        return _RECIPE_DIR.joinpath(*parts[1:-1]) / f"{parts[-1]}.md"
    return _RECIPE_DIR / f"{_slug(skillId)}.md"


def proposeRecipe(
    id: str,
    title: str,
    *,
    purpose: str = "",
    gap: dict[str, Any] | None = None,
    falsifier: dict[str, Any] | None = None,
    expectedNovelty: list[str] | None = None,
    testUniverse: dict[str, Any] | None = None,
    linkedSkills: list[str] | None = None,
    requiredEvidence: list[str] | None = None,
    body: str = "",
) -> ToolResult:
    """recipe markdown spec 신규 작성. status = drafted.

    Parameters
    ----------
    id : str
        ``recipes.<persona>[.<domain>...].<slug>`` 형식 (≥3 parts, depth 가변).
        예: ``recipes.fundamental.dividend.thesis``, ``recipes.fundamental.valuation.damodaran.fcffDcf``.
        동일 id 가 이미 존재하면 거부.
    title : str
        한국어 제목. 공백만이면 거부.
    purpose : str, optional
        한 줄 목적. 미지정시 frontmatter 에 빈 값.
    gap : dict, required-by-lint
        ``{primary: [엔진1, 엔진2], secondary: [...optional]}``. 미지정시 본 함수가 거부.
    falsifier : dict, required-by-lint
        ``{description: "...", pythonCheck: "..."}``. description 비어있으면 거부.
    expectedNovelty : list[str], optional
        recipe 출력이 단일 엔진 컬럼셋 외에 새로 추가하는 컬럼 이름 목록.
    testUniverse : dict, optional
        ``{market: KR, stockCodes: [...], asOfPolicy: latest|fixed:YYYY-MM-DD}``.
    linkedSkills : list[str], optional
        recipe 가 호출하는 skill id 목록.
    requiredEvidence : list[str], optional
        ``[skillRef, tableRef, valueRef, dateRef]`` 등.
    body : str, optional
        markdown 본문. 비어있으면 placeholder ``## 공개 호출 방식`` 안내문 작성.

    Returns
    -------
    ToolResult
        ok=True 면 ``data.path`` 에 새 spec 경로, refs 에 skillRef.

    Notes
    -----
    AI 가 사용자 질문에 자율적으로 호출하는 도구 — workbench HARVEST 자동 호출 X.
    승격은 항상 운영자 CLI (`src/dartlab/skills/recipePromote.py promote <id>`) 단독.
    """
    skill_id = (id or "").strip()
    if not skill_id:
        return ToolResult(False, "id 가 비어 있다", error="missing_id")
    parts = skill_id.split(".")
    if len(parts) < 3 or parts[0] != "recipes" or not all(parts[1:]):
        return ToolResult(
            False,
            f"id 는 'recipes.<persona>[.<domain>...].<slug>' 형식 (≥3 parts, got {skill_id!r})",
            error="invalid_id_prefix",
        )
    if not (title or "").strip():
        return ToolResult(False, "title 이 비어 있다", error="missing_title")

    err = _validateGap(gap)
    if err:
        return ToolResult(False, err, error="invalid_gap")

    err = _validateFalsifier(falsifier)
    if err:
        return ToolResult(False, err, error="invalid_falsifier")

    target_path = _recipePath(skill_id)
    if target_path.exists():
        return ToolResult(
            False,
            f"이미 동일한 recipe 가 존재한다: {target_path.name}",
            error="recipe_already_exists",
        )

    frontmatter: dict[str, Any] = {
        "id": skill_id,
        "title": title.strip(),
        "category": "recipes",
        "kind": "recipe",
        "scope": "builtin",
        "status": "drafted",
    }
    if purpose:
        frontmatter["purpose"] = purpose
    if linkedSkills:
        frontmatter["linkedSkills"] = list(linkedSkills)
    if requiredEvidence:
        frontmatter["requiredEvidence"] = list(requiredEvidence)
    frontmatter["gap"] = dict(gap or {})
    if testUniverse:
        frontmatter["testUniverse"] = dict(testUniverse)
    frontmatter["falsifier"] = dict(falsifier or {})
    if expectedNovelty:
        frontmatter["expectedNovelty"] = list(expectedNovelty)

    body_text = (body or "").strip()
    if not body_text:
        body_text = (
            "## 공개 호출 방식\n\n"
            "```python\nimport dartlab\n# TODO: recipe 절차 작성\n```\n\n"
            "## 호출 동작\n\n"
            "1. (단계 작성)\n\n"
            "## 대표 반환 형태\n\n"
            "(반환 dict / DataFrame 컬럼 명세)\n\n"
            "## 연계 절차\n\n"
            "- (linkedSkills 의 사용 순서 작성)\n"
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    head = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    target_path.write_text(f"---\n{head}\n---\n\n{body_text}\n", encoding="utf-8")

    ref = Ref(
        id=f"skill:{skill_id}",
        kind="skillRef",
        title=title.strip(),
        source=f"dartlab://skills/{skill_id}",
        payload={
            "path": str(target_path),
            "status": "drafted",
            "kind": "recipe",
        },
    )
    return ToolResult(
        True,
        f"신규 recipe 후보 작성 (status=drafted): {target_path.name}",
        refs=[ref],
        data={"path": str(target_path), "id": skill_id},
    )


__all__ = ["proposeRecipe"]
