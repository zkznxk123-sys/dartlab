"""Damodaran L1.5 recipe guard tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[1]
DAMODARAN_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes" / "valuation" / "damodaran"
REFERENCE_DATA = REPO_ROOT / "src" / "dartlab" / "reference" / "data"

DAMODARAN_IDS = {
    "recipes.valuation.damodaran.dataAudit",
    "recipes.valuation.damodaran.businessModelFit",
    "recipes.valuation.damodaran.normalizedFinancials",
    "recipes.valuation.damodaran.reinvestmentRoc",
    "recipes.valuation.damodaran.costOfCapital",
    "recipes.valuation.damodaran.fcffDcf",
    "recipes.valuation.damodaran.relativeCheck",
    "recipes.valuation.damodaran.scenarioFalsifier",
    "recipes.valuation.damodaran.deepDive",
}

BANNED_L2_CALLS = (
    "c.analysis",
    "c.quant",
    "c.credit",
    "c.industry",
    "c.story",
    "dartlab.analysis",
    "dartlab.quant",
    "dartlab.credit",
    "dartlab.industry",
    "dartlab.story",
    "dartlab.macro",
)


def _publicCallSection(text: str) -> str:
    marker = "## 공개 호출 방식"
    start = text.find(marker)
    assert start >= 0, "missing public call section"
    section = text[start + len(marker) :]
    next_h2 = section.find("\n## ")
    return section if next_h2 < 0 else section[:next_h2]


def _pythonBlocks(text: str) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def testDamodaranRecipeSpecsLoadAsUnverifiedRecipes() -> None:
    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    specs = {spec.id: spec for spec in listSkills(includeUser=False)}

    assert DAMODARAN_IDS <= set(specs)
    for skillId in DAMODARAN_IDS:
        spec = specs[skillId]
        assert spec.kind == "recipe"
        assert spec.category == "recipes"
        assert spec.status == "unverified"
        assert spec.linkedSkills or "## 연계 절차" in spec.source.get("body", "")


def testDamodaranPublicCallBlocksStayBelowL2() -> None:
    failures: list[str] = []
    for path in sorted(DAMODARAN_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        for token in BANNED_L2_CALLS:
            if token in section:
                failures.append(f"{path.name}: banned L2 call {token}")

    assert not failures, "Damodaran L1.5 recipes must not call L2/L3 engines\n" + "\n".join(failures)


def testDamodaranPublicCallBlocksParseAsPython() -> None:
    failures: list[str] = []
    for path in sorted(DAMODARAN_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        blocks = _pythonBlocks(section)
        if not blocks:
            failures.append(f"{path.name}: no python block")
            continue
        for idx, code in enumerate(blocks):
            try:
                ast.parse(code)
            except SyntaxError as exc:
                failures.append(f"{path.name} block {idx}: {exc.msg} line {exc.lineno}")

    assert not failures, "Damodaran recipe code blocks must be AST-parseable\n" + "\n".join(failures)


def testDamodaranReferenceDataHasStaleAndSourceGates() -> None:
    country = json.loads((REFERENCE_DATA / "damodaranDefaults.json").read_text(encoding="utf-8"))
    industry = json.loads((REFERENCE_DATA / "damodaranIndustryDefaults.json").read_text(encoding="utf-8"))

    assert country["_meta"]["freshnessStatus"] in {"fresh", "stale"}
    assert country["_meta"]["maxStaleDays"] > 0
    assert country["_meta"]["url"].startswith("https://pages.stern.nyu.edu/")
    assert {"KR", "US"} <= set(country["countries"])

    assert industry["_meta"]["coverageStatus"] == "seed-subset"
    assert {"betas", "costOfCapital", "cashFlowDrivers", "margins"} <= set(industry["_meta"]["sourceUrls"])
    assert "semiconductor" in industry["industries"]
    assert "totalMarketWithoutFinancials" in industry["industries"]
    assert industry["gapLedger"], "industry defaults must expose remaining L1.5 gaps"


def testDamodaranErpUpdaterTargetsReferenceData() -> None:
    script = (REPO_ROOT / "scripts" / "data" / "updateDamodaranERP.py").read_text(encoding="utf-8")

    assert '"reference" / "data" / "damodaranDefaults.json"' in script
    assert '"core" / "data" / "damodaranDefaults.json"' not in script
