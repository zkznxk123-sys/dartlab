"""Thesis kill-chain incubator recipe guard tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
KILL_CHAIN_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes" / "incubator" / "thesisKillChain"

KILL_CHAIN_IDS = {
    "recipes.incubator.thesisKillChain.index",
    "recipes.incubator.thesisKillChain.thesisIntake",
    "recipes.incubator.thesisKillChain.evidenceCoverageAudit",
    "recipes.incubator.thesisKillChain.assumptionLedger",
    "recipes.incubator.thesisKillChain.fragilityMap",
    "recipes.incubator.thesisKillChain.triggerCatalog",
    "recipes.incubator.thesisKillChain.propagationPath",
    "recipes.incubator.thesisKillChain.tripwireMonitor",
    "recipes.incubator.thesisKillChain.falsifierLedger",
    "recipes.incubator.thesisKillChain.scenarioStoryboard",
    "recipes.incubator.thesisKillChain.visualDecisionPack",
    "recipes.incubator.thesisKillChain.deepDive",
}

BANNED_L2_CALLS = (
    "c.analysis",
    "c.quant",
    "c.credit",
    "c.macro",
    "c.industry",
    "c.story",
    "dartlab.analysis",
    "dartlab.quant",
    "dartlab.credit",
    "dartlab.macro",
    "dartlab.industry",
    "dartlab.story",
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


def testThesisKillChainRecipeSpecsLoadAsObservedRecipes() -> None:
    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    specs = {spec.id: spec for spec in listSkills(includeUser=False)}

    assert KILL_CHAIN_IDS <= set(specs)
    for skill_id in KILL_CHAIN_IDS:
        spec = specs[skill_id]
        assert spec.kind == "recipe"
        assert spec.category == "recipes"
        assert spec.status == "observed"
        assert spec.graphTier == "L1.5"
        assert spec.requiredEvidence
        assert spec.expectedOutputs
        assert set(spec.capabilityRefs) & {
            "Company.show",
            "Company.disclosure",
            "Company.gather",
            "scan.market",
            "scan.audit",
            "scan.quality",
        }


def testThesisKillChainSkillsAreExposedThroughAiEntryPoints() -> None:
    from dartlab.ai.tools.readSkill import getSkillBody, readSkill

    entry = readSkill("thesis kill chain 프리모템 투자 논리 깨보기", limit=8, includeUser=False)
    path = readSkill("thesisKillChain propagation path trigger assumption", limit=8, includeUser=False)
    scenario = readSkill("thesisKillChain scenario storyboard base erosion kill", limit=8, includeUser=False)

    assert entry.ok
    assert entry.data["skills"][0]["id"] == "recipes.incubator.thesisKillChain.index"
    assert path.ok
    assert path.data["skills"][0]["id"] == "recipes.incubator.thesisKillChain.propagationPath"
    assert scenario.ok
    assert scenario.data["skills"][0]["id"] == "recipes.incubator.thesisKillChain.scenarioStoryboard"

    body = getSkillBody("recipes.incubator.thesisKillChain.deepDive", includeUser=False)
    assert body.ok
    raw = body.data["body"]
    assert "buildThesisKillChainMemo" in raw
    assert "recipes.incubator.thesisKillChain.scenarioStoryboard" in raw


def testThesisKillChainSkillsAreInPublicSkillArtifacts() -> None:
    artifact_dir = REPO_ROOT / "src" / "dartlab" / "skills"

    for name in ("index.json", "agent.json", "web.json", "mcp.json", "pyodide.json"):
        payload = json.loads((artifact_dir / name).read_text(encoding="utf-8"))
        rows = payload.get("skills", [])
        by_id = {row["id"]: row for row in rows}

        assert KILL_CHAIN_IDS <= set(by_id), f"{name} missing thesis kill-chain skill rows"
        if name != "pyodide.json":
            assert payload["meta"]["skillCount"] == len(rows)
            recipe_meta = [row for row in payload["meta"]["categories"] if row["id"] == "recipes"]
            assert recipe_meta and recipe_meta[0]["count"] == sum(row.get("category") == "recipes" for row in rows)
        if name in {"index.json", "agent.json", "mcp.json"}:
            assert by_id["recipes.incubator.thesisKillChain.index"]["bodyPreview"]
        if name in {"index.json", "agent.json", "web.json"}:
            assert by_id["recipes.incubator.thesisKillChain.deepDive"]["expectedOutputs"]
        if name == "web.json":
            assert by_id["recipes.incubator.thesisKillChain.index"]["bodyHuman"]

    graph = json.loads((artifact_dir / "graph.json").read_text(encoding="utf-8"))
    graph_ids = {node["id"] for node in graph.get("nodes", [])}
    assert KILL_CHAIN_IDS <= graph_ids


def testThesisKillChainPublicCallBlocksStayBelowL2() -> None:
    failures: list[str] = []
    for path in sorted(KILL_CHAIN_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        for token in BANNED_L2_CALLS:
            if token in section:
                failures.append(f"{path.name}: banned L2 call {token}")

    assert not failures, "Thesis kill-chain recipes must not call L2 engines\n" + "\n".join(failures)


def testThesisKillChainPublicCallBlocksParseAsPython() -> None:
    failures: list[str] = []
    for path in sorted(KILL_CHAIN_DIR.glob("*.md")):
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

    assert not failures, "Thesis kill-chain recipe code blocks must be AST-parseable\n" + "\n".join(failures)


def testThesisKillChainPublicCallBlocksUseL15MemoBuilder() -> None:
    failures: list[str] = []
    for path in sorted(KILL_CHAIN_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        if 'target = "005930"' not in section:
            failures.append(f"{path.name}: missing default target placeholder")
        if "buildThesisKillChainMemo" not in section:
            failures.append(f"{path.name}: missing L1.5 memo builder")
        if 'sources=memo["sources"]' not in section:
            failures.append(f"{path.name}: missing sourceRef payload")

    assert not failures, "Thesis kill-chain recipes must execute the L1.5 helper\n" + "\n".join(failures)


def testThesisKillChainVisualRefsUseObservedVizSkillsOnly() -> None:
    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    specs = {spec.id: spec for spec in listSkills(includeUser=False)}

    for skill_id in KILL_CHAIN_IDS:
        spec = specs[skill_id]
        for visual_ref in spec.visualRefs:
            assert visual_ref.startswith("engines.viz.")
            assert specs[visual_ref].status == "observed"


def _sampleStatements() -> dict[str, pl.DataFrame]:
    years = ["2025", "2024", "2023"]

    def row(snake: str, values: list[float]) -> dict[str, float | str]:
        return {"snakeId": snake, "항목": snake, **dict(zip(years, values, strict=True))}

    return {
        "IS": pl.DataFrame(
            [
                row("sales", [800.0, 1000.0, 920.0]),
                row("operating_profit", [40.0, 140.0, 120.0]),
                row("net_income", [30.0, 120.0, 100.0]),
            ]
        ),
        "BS": pl.DataFrame(
            [
                row("cash_and_cash_equivalents", [90.0, 120.0, 110.0]),
                row("borrowings", [820.0, 760.0, 700.0]),
                row("total_stockholders_equity", [450.0, 500.0, 470.0]),
            ]
        ),
        "CF": pl.DataFrame(
            [
                row("operating_cashflow", [10.0, 130.0, 105.0]),
                row("purchase_of_property_plant_and_equipment", [-180.0, -150.0, -120.0]),
            ]
        ),
    }


def testThesisKillChainSynthBuildsDeepPremortemFromL15Inputs() -> None:
    from dartlab.synth.thesisKillChain import buildThesisKillChainMemo

    memo = buildThesisKillChainMemo(
        target="SAMPLE",
        market="KR",
        companyName="Sample Platform",
        thesis="매출 성장과 마진 회복, 현금 전환이 유지되어 valuation discount가 해소된다",
        statements=_sampleStatements(),
        filings=[
            {"rcept_dt": "20260510", "report_nm": "전환사채 발행 결정"},
            {"rcept_dt": "20260501", "report_nm": "사업보고서 정정 공시"},
        ],
        priceRows=[
            {"date": "2026-05-11", "close": 88000.0},
            {"date": "2026-05-10", "close": 100000.0},
        ],
        flowRows=[{"date": "2026-05-11", "foreignNetBuy": -12_000_000.0, "institutionNetBuy": -5_000_000.0}],
        consensusRows=[
            {"date": "2026-05-11", "opConsensus": 90.0},
            {"date": "2026-04-25", "opConsensus": 130.0},
        ],
        scanRows=[
            {"target": "SAMPLE", "axis": "audit", "score": 2.0},
            {"target": "SAMPLE", "axis": "quality", "score": 1.0},
        ],
        assumptions=["성장 둔화가 없다", "영업현금흐름이 순이익을 따라온다"],
    )

    assert memo["decisionStatus"] == "usable"
    assert memo["headline"]["killRiskScore"] >= 20
    assert memo["headline"]["assumptionCount"] >= 3
    assert memo["headline"]["openTripwireCount"] >= 5
    assert {
        "thesisIntake",
        "evidenceCoverageAudit",
        "assumptionLedger",
        "fragilityMap",
        "triggerCatalog",
        "propagationPath",
        "tripwireMonitor",
        "falsifierLedger",
        "scenarioStoryboard",
        "visualDecisionPack",
        "deepDive",
    } <= set(memo["tables"])
    assert len(memo["tables"]["deepDive"]) == 11
    assert memo["tables"]["deepDive"][-1]["step"] == "finalDecision"
    assert {row["scenario"] for row in memo["tables"]["scenarioStoryboard"]} == {
        "baseIntact",
        "erosionCase",
        "killChainCase",
    }
    assert any(row["metric"] == "cashConversion" and row["status"] == "risk" for row in memo["tables"]["fragilityMap"])
    assert any(row["triggerId"].startswith("filing:financingStress") for row in memo["tables"]["triggerCatalog"])
    assert any(row["status"] == "open" for row in memo["tables"]["falsifierLedger"])
    assert all(row["status"] == "ready" for row in memo["tables"]["visualDecisionPack"])
    assert any(source["id"] == "l15ThesisKillChain" for source in memo["sources"])
