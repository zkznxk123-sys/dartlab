"""Recipe execution contract guards."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS = REPO_ROOT / "src" / "dartlab" / "skills" / "specs"

KEY_RECIPE_PATHS = [
    SPECS / "recipes" / "fundamental" / "quality" / "forensics" / "index.md",
    SPECS / "recipes" / "fundamental" / "quality" / "forensics" / "deepDive.md",
    SPECS / "recipes" / "fundamental" / "valuation" / "damodaran" / "index.md",
    SPECS / "recipes" / "fundamental" / "valuation" / "damodaran" / "deepDive.md",
]


def _frontmatter(text: str) -> str:
    match = re.match(r"---\n(.*?)\n---", text, flags=re.DOTALL)
    assert match, "missing frontmatter"
    return match.group(1)


def _listField(frontmatter: str, field: str) -> list[str]:
    lines = frontmatter.splitlines()
    values: list[str] = []
    in_field = False
    for line in lines:
        if line.startswith(f"{field}:"):
            in_field = True
            continue
        if in_field:
            if line and not line.startswith(" "):
                break
            stripped = line.strip()
            if stripped.startswith("- "):
                values.append(stripped[2:].strip().strip('"').strip("'"))
    return values


def _publicCallSection(text: str) -> str:
    marker = "## 공개 호출 방식"
    start = text.find(marker)
    assert start >= 0, "missing public call section"
    section = text[start + len(marker) :]
    next_h2 = section.find("\n## ")
    return section if next_h2 < 0 else section[:next_h2]


def _vizStatuses() -> dict[str, str]:
    statuses: dict[str, str] = {}
    for path in sorted((SPECS / "engines" / "viz").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        front = _frontmatter(text)
        skill_id = re.search(r"(?m)^id:\s*\"?([^\"\n]+)\"?", front)
        status = re.search(r"(?m)^status:\s*\"?([^\"\n]+)\"?", front)
        if skill_id and status:
            statuses[skill_id.group(1).strip()] = status.group(1).strip()
    return statuses


def testKeyRecipesPreferEngineCallBeforeRunPython() -> None:
    for path in KEY_RECIPE_PATHS:
        front = _frontmatter(path.read_text(encoding="utf-8"))
        tools = _listField(front, "toolRefs")
        assert "EngineCall" in tools, f"{path.name} missing EngineCall"
        assert "RunPython" in tools, f"{path.name} missing RunPython fallback"
        assert tools.index("EngineCall") < tools.index("RunPython"), f"{path.name} must list EngineCall first"


def testKeyRecipesDocumentRunPythonAsFallback() -> None:
    for path in KEY_RECIPE_PATHS:
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        assert "EngineCall" in section, f"{path.name} public call must mention EngineCall first"
        assert "RunPython fallback" in section or "RunPython 폴백" in section, (
            f"{path.name} must label Python block as fallback"
        )


def testKeyRecipeVisualRefsUseObservedVizSkillsOnly() -> None:
    statuses = _vizStatuses()
    for path in KEY_RECIPE_PATHS:
        front = _frontmatter(path.read_text(encoding="utf-8"))
        for visual_ref in _listField(front, "visualRefs"):
            assert visual_ref in statuses, f"{path.name} unknown visualRef {visual_ref}"
            assert statuses[visual_ref] == "observed", f"{path.name} visualRef {visual_ref} is not observed"


def testSchemaDefinesEngineToolCardAndRecipeFallbackContract() -> None:
    schema = (REPO_ROOT / "src" / "dartlab" / "skills" / "SCHEMA.md").read_text(encoding="utf-8")
    assert "엔진 skill 은 **tool card**" in schema
    assert "Recipe 는 RunPython 스크립트 모음이 아니라 **엔진 호출 오케스트레이션**" in schema
    assert "EngineCall 우선" in schema
    assert "RunPython fallback" in schema
    assert "observed viz skill 우선" in schema
