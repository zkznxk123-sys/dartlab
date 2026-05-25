"""Damodaran L1.5 recipe guard tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
DAMODARAN_DIR = (
    REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes" / "fundamental" / "valuation" / "damodaran"
)
REFERENCE_DATA = REPO_ROOT / "src" / "dartlab" / "reference" / "data"

DAMODARAN_IDS = {
    "recipes.fundamental.valuation.damodaran.index",
    "recipes.fundamental.valuation.damodaran.dataAudit",
    "recipes.fundamental.valuation.damodaran.businessModelFit",
    "recipes.fundamental.valuation.damodaran.lifeCycleClassifier",
    "recipes.fundamental.valuation.damodaran.narrativeMap",
    "recipes.fundamental.valuation.damodaran.storyToDrivers",
    "recipes.fundamental.valuation.damodaran.normalizedFinancials",
    "recipes.fundamental.valuation.damodaran.accountTraceAudit",
    "recipes.fundamental.valuation.damodaran.rdCapitalization",
    "recipes.fundamental.valuation.damodaran.leaseDebtAdjustment",
    "recipes.fundamental.valuation.damodaran.oneOffAdjustment",
    "recipes.fundamental.valuation.damodaran.reinvestmentRoc",
    "recipes.fundamental.valuation.damodaran.growthFeasibility",
    "recipes.fundamental.valuation.damodaran.costOfCapital",
    "recipes.fundamental.valuation.damodaran.fcffDcf",
    "recipes.fundamental.valuation.damodaran.relativeCheck",
    "recipes.fundamental.valuation.damodaran.peerMultipleDecomposition",
    "recipes.fundamental.valuation.damodaran.financialFirmExcessReturn",
    "recipes.fundamental.valuation.damodaran.sumOfParts",
    "recipes.fundamental.valuation.damodaran.distressAdjustedDcf",
    "recipes.fundamental.valuation.damodaran.scenarioFalsifier",
    "recipes.fundamental.valuation.damodaran.deepDive",
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
        assert spec.status == "tested"
        assert spec.linkedSkills or "## 연계 절차" in spec.source.get("body", "")
        assert spec.expectedOutputs, f"{skillId} must declare expectedOutputs before promotion review"


def testDamodaranSkillsAreExposedThroughAiEntryPoints() -> None:
    from dartlab.ai.tools.readSkill import getSkillBody, readSkill

    entry = readSkill("다모다란 분석 최초 진입점 L1 L1.5", limit=6, includeUser=False)
    narrative = readSkill("Damodaran narrative and numbers story drivers", limit=6, includeUser=False)
    financial = readSkill("금융업 은행 보험 Damodaran excess return 가치평가", limit=6, includeUser=False)
    peer = readSkill("peer multiple decomposition 다모다란 상대가치", limit=6, includeUser=False)

    assert entry.ok
    assert entry.data["skills"][0]["id"] == "recipes.fundamental.valuation.damodaran.index"
    assert entry.data["skills"][0]["expectedOutputs"]
    assert narrative.ok
    assert narrative.data["skills"][0]["id"] == "recipes.fundamental.valuation.damodaran.storyToDrivers"
    assert narrative.data["skills"][0]["expectedOutputs"]
    assert financial.ok
    assert financial.data["skills"][0]["id"] == "recipes.fundamental.valuation.damodaran.financialFirmExcessReturn"
    assert peer.ok
    assert peer.data["skills"][0]["id"] == "recipes.fundamental.valuation.damodaran.peerMultipleDecomposition"

    body = getSkillBody("recipes.fundamental.valuation.damodaran.deepDive", includeUser=False)
    assert body.ok
    raw = body.data["body"]
    assert "recipes.fundamental.valuation.damodaran.storyToDrivers" in raw
    assert "recipes.fundamental.valuation.damodaran.distressAdjustedDcf" in raw


def testDamodaranSkillsAreInPublicSkillArtifacts() -> None:
    artifact_dir = REPO_ROOT / "src" / "dartlab" / "skills"

    for name in ("index.json", "agent.json", "web.json", "mcp.json", "pyodide.json"):
        payload = json.loads((artifact_dir / name).read_text(encoding="utf-8"))
        rows = payload.get("skills", [])
        by_id = {row["id"]: row for row in rows}

        assert DAMODARAN_IDS <= set(by_id), f"{name} missing Damodaran skill rows"
        if name != "pyodide.json":
            assert payload["meta"]["skillCount"] == len(rows)
            recipe_meta = [row for row in payload["meta"]["categories"] if row["id"] == "recipes"]
            assert recipe_meta and recipe_meta[0]["count"] == sum(row.get("category") == "recipes" for row in rows)
        if name in {"index.json", "agent.json", "mcp.json"}:
            assert by_id["recipes.fundamental.valuation.damodaran.index"]["bodyPreview"]
        if name in {"index.json", "agent.json", "web.json"}:
            assert by_id["recipes.fundamental.valuation.damodaran.deepDive"]["expectedOutputs"]
        if name == "web.json":
            assert by_id["recipes.fundamental.valuation.damodaran.index"]["bodyHuman"]

    graph = json.loads((artifact_dir / "graph.json").read_text(encoding="utf-8"))
    graph_ids = {node["id"] for node in graph.get("nodes", [])}
    assert DAMODARAN_IDS <= graph_ids


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


def testDamodaranPublicCallBlocksUseL15MemoBuilder() -> None:
    failures: list[str] = []
    for path in sorted(DAMODARAN_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        if path.name == "index.md":
            if "damodaranAnalysisSystem.json" not in section:
                failures.append(f"{path.name}: missing analysis system reference")
            if "sources=sources" not in section:
                failures.append(f"{path.name}: missing sourceRef payload")
            continue
        if 'target = "005930"' not in section:
            failures.append(f"{path.name}: missing default target placeholder")
        if "buildDamodaranMemo" not in section:
            failures.append(f"{path.name}: missing L1.5 memo builder")
        if 'sources=memo["sources"]' not in section:
            failures.append(f"{path.name}: missing sourceRef payload")

    assert not failures, "Damodaran recipes must execute the L1.5 valuation helper\n" + "\n".join(failures)


def _sampleStatements() -> dict[str, pl.DataFrame]:
    years = ["2025", "2024", "2023", "2022", "2021", "2020"]
    revenue = [1200.0, 1100.0, 1000.0, 930.0, 860.0, 800.0]
    ebit = [240.0, 210.0, 180.0, 150.0, 120.0, 100.0]
    pretax = [230.0, 200.0, 170.0, 140.0, 110.0, 90.0]
    taxes = [55.0, 48.0, 41.0, 34.0, 26.0, 21.0]
    cash = [100.0, 92.0, 84.0, 80.0, 76.0, 72.0]
    equity = [900.0, 830.0, 760.0, 700.0, 650.0, 600.0]
    short_debt = [40.0, 38.0, 36.0, 34.0, 32.0, 30.0]
    long_debt = [120.0, 115.0, 110.0, 105.0, 100.0, 95.0]
    receivables = [180.0, 160.0, 145.0, 130.0, 120.0, 110.0]
    inventory = [150.0, 140.0, 130.0, 120.0, 110.0, 100.0]
    payables = [90.0, 82.0, 76.0, 70.0, 65.0, 60.0]
    cfo = [220.0, 205.0, 190.0, 170.0, 150.0, 135.0]
    capex = [-95.0, -90.0, -84.0, -78.0, -70.0, -66.0]
    depreciation = [50.0, 48.0, 45.0, 42.0, 40.0, 38.0]

    def row(snake: str, values: list[float]) -> dict[str, float | str]:
        return {"snakeId": snake, "항목": snake, **dict(zip(years, values, strict=True))}

    return {
        "IS": pl.DataFrame(
            [
                row("sales", revenue),
                row("operating_profit", ebit),
                row("profit_before_tax", pretax),
                row("income_taxes", taxes),
            ]
        ),
        "BS": pl.DataFrame(
            [
                row("cash_and_cash_equivalents", cash),
                row("total_stockholders_equity", equity),
                row("short_term_debt", short_debt),
                row("long_term_debt", long_debt),
                row("trade_and_other_receivables", receivables),
                row("inventories", inventory),
                row("trade_and_other_payables", payables),
            ]
        ),
        "CF": pl.DataFrame(
            [
                row("operating_cashflow", cfo),
                row("purchase_of_property_plant_and_equipment", capex),
                row("depreciation_cf", depreciation),
            ]
        ),
    }


def _damodaranReferences() -> tuple[dict, dict]:
    country = json.loads((REFERENCE_DATA / "damodaranDefaults.json").read_text(encoding="utf-8"))
    industry = json.loads((REFERENCE_DATA / "damodaranIndustryDefaults.json").read_text(encoding="utf-8"))
    return country, industry


def testDamodaranSynthBuildsFullMemoFromL15Inputs() -> None:
    from dartlab.synth.damodaranL15 import buildDamodaranMemo

    country, industry = _damodaranReferences()
    memo = buildDamodaranMemo(
        target="SAMPLE",
        market="US",
        currency="USD",
        companyName="Sample Semiconductor",
        statements=_sampleStatements(),
        countryDefaults=country,
        industryDefaults=industry,
        marketData={"marketCap": 1_250.0, "shares": 100.0, "priceDate": "2026-05-14"},
        industryKey="semiconductor",
    )

    assert memo["decisionStatus"] in {"usable", "usableWithFallback"}
    assert memo["headline"]["baseEquityValue"] is not None
    assert memo["reverseDcf"]["status"] == "usable"
    assert memo["tables"]["normalizedFinancials"][0]["fcff"] is not None
    assert {
        "dataAudit",
        "modelFit",
        "lifeCycleClassifier",
        "narrativeMap",
        "storyToDrivers",
        "normalizedFinancials",
        "accountTraceAudit",
        "rdCapitalization",
        "leaseDebtAdjustment",
        "oneOffAdjustment",
        "reinvestmentRoc",
        "growthFeasibility",
        "fcffDcf",
        "peerMultipleDecomposition",
        "financialFirmExcessReturn",
        "sumOfParts",
        "distressAdjustedDcf",
        "scenarioFalsifier",
        "deepDive",
    } <= set(memo["tables"])
    assert len(memo["tables"]["deepDive"]) == 21
    deep_dive_steps = {row["step"] for row in memo["tables"]["deepDive"]}
    assert {
        "dataAudit",
        "businessModelFit",
        "narrativeMap",
        "storyToDrivers",
        "normalizedFinancials",
        "fcffDcf",
        "scenarioFalsifier",
        "finalDecision",
    } <= deep_dive_steps
    assert {"order", "step", "status", "evidence", "fallbackCount", "blockerCount", "nextAction"} <= set(
        memo["tables"]["deepDive"][0]
    )
    assert memo["tables"]["lifeCycleClassifier"][0]["metric"] == "lifeCyclePhase"
    assert any(row["traceKey"] == "revenue" for row in memo["tables"]["accountTraceAudit"])
    assert any(row["metric"] == "growthFeasibility" for row in memo["tables"]["growthFeasibility"])
    assert any(source["id"] == "damodaranCountryRiskPremiums" for source in memo["sources"])


def testDamodaranSynthBlocksGenericFcffForFinancialFirms() -> None:
    from dartlab.synth.damodaranL15 import buildDamodaranMemo

    country, industry = _damodaranReferences()
    memo = buildDamodaranMemo(
        target="138930",
        market="KR",
        currency="KRW",
        companyName="BNK금융지주",
        statements=_sampleStatements(),
        countryDefaults=country,
        industryDefaults=industry,
        marketData={"marketCap": 1_250.0, "shares": 100.0, "priceDate": "2026-05-14"},
        industryKey="banksRegional",
    )

    assert memo["decisionStatus"] == "blockedFinancialFirm"
    assert memo["dcfBand"]["status"] == "blocked"
    assert memo["modelFit"]["fallbackModel"] == "financialFirmExcessReturn"


def testRunPythonEmitResultCreatesSourceRefs() -> None:
    from dartlab.ai.tools.runPython import runPython

    result = runPython(
        'emit_result(values={"x": 1}, sources=[{"id": "sourceA", "title": "Source A", "url": "https://example.com"}])',
        runId="source-unit",
    )

    assert result.ok
    assert any(ref.kind == "sourceRef" and ref.id.endswith(":sourceA") for ref in result.refs)


def testDamodaranReferenceDataHasStaleAndSourceGates() -> None:
    country = json.loads((REFERENCE_DATA / "damodaranDefaults.json").read_text(encoding="utf-8"))
    industry = json.loads((REFERENCE_DATA / "damodaranIndustryDefaults.json").read_text(encoding="utf-8"))
    system = json.loads((REFERENCE_DATA / "damodaranAnalysisSystem.json").read_text(encoding="utf-8"))

    assert country["_meta"]["freshnessStatus"] in {"fresh", "stale"}
    assert country["_meta"]["maxStaleDays"] > 0
    assert country["_meta"]["url"].startswith("https://pages.stern.nyu.edu/")
    assert {"KR", "US"} <= set(country["countries"])

    assert industry["_meta"]["coverageStatus"] == "seed-subset"
    assert {"betas", "costOfCapital", "cashFlowDrivers", "margins"} <= set(industry["_meta"]["sourceUrls"])
    assert "semiconductor" in industry["industries"]
    assert "totalMarketWithoutFinancials" in industry["industries"]
    assert industry["gapLedger"], "industry defaults must expose remaining L1.5 gaps"

    assert system["_meta"]["coverageStatus"] == "system-contract-v1"
    assert system["skillTree"]["entrySkill"] == "recipes.fundamental.valuation.damodaran.index"
    assert system["promotionReadiness"]["status"] == "operatorReviewReady"
    assert system["promotionReadiness"]["skillCount"] == len(DAMODARAN_IDS)
    assert system["promotionReadiness"]["executionSkillCount"] == len(DAMODARAN_IDS) - 1
    assert system["promotionReadiness"]["validationSummary"]["minimumExecutionPassRate"] >= 1.0
    assert system["promotionReadiness"]["validationSummary"]["minimumEvidenceCompleteness"] >= 1.0
    assert system["promotionReadiness"]["validationSummary"]["missingEvidenceCount"] == 0
    assert {route["target"] for route in system["promotionReadiness"]["dogfoodRoutes"]} >= {"005930", "AAPL", "138930"}
    assert system["promotionReadiness"]["promotionBlockers"]
    assert {
        "recipes.fundamental.valuation.damodaran.lifeCycleClassifier",
        "recipes.fundamental.valuation.damodaran.accountTraceAudit",
        "recipes.fundamental.valuation.damodaran.growthFeasibility",
        "recipes.fundamental.valuation.damodaran.narrativeMap",
        "recipes.fundamental.valuation.damodaran.storyToDrivers",
        "recipes.fundamental.valuation.damodaran.rdCapitalization",
        "recipes.fundamental.valuation.damodaran.leaseDebtAdjustment",
        "recipes.fundamental.valuation.damodaran.oneOffAdjustment",
        "recipes.fundamental.valuation.damodaran.peerMultipleDecomposition",
        "recipes.fundamental.valuation.damodaran.financialFirmExcessReturn",
        "recipes.fundamental.valuation.damodaran.sumOfParts",
        "recipes.fundamental.valuation.damodaran.distressAdjustedDcf",
    } <= set(system["skillTree"]["currentExecutablePath"])
    assert {
        "recipes.fundamental.valuation.damodaran.lifeCycleClassifier",
        "recipes.fundamental.valuation.damodaran.accountTraceAudit",
        "recipes.fundamental.valuation.damodaran.growthFeasibility",
        "recipes.fundamental.valuation.damodaran.narrativeMap",
        "recipes.fundamental.valuation.damodaran.storyToDrivers",
        "recipes.fundamental.valuation.damodaran.rdCapitalization",
        "recipes.fundamental.valuation.damodaran.leaseDebtAdjustment",
        "recipes.fundamental.valuation.damodaran.oneOffAdjustment",
        "recipes.fundamental.valuation.damodaran.peerMultipleDecomposition",
        "recipes.fundamental.valuation.damodaran.financialFirmExcessReturn",
        "recipes.fundamental.valuation.damodaran.sumOfParts",
        "recipes.fundamental.valuation.damodaran.distressAdjustedDcf",
    }.isdisjoint(system["skillTree"]["nextSkillTargets"])
    assert system["skillTree"]["nextSkillTargets"] == []
    assert len(system["concepts"]) == 10
    assert {concept["id"] for concept in system["concepts"]} == {
        "narrativeAndNumbers",
        "businessLifeCycle",
        "financialStatementNormalization",
        "valueDrivers",
        "riskAndCostOfCapital",
        "intrinsicValuation",
        "relativeValuation",
        "specialSituations",
        "falsificationReverseDcf",
        "valuationMemoStoryboard",
    }
    for concept in system["concepts"]:
        assert concept["implementedSkills"]
        assert isinstance(concept["plannedSkills"], list)
        assert concept["dataRequirements"]
        assert concept["gapIds"]

    allowed_gap_status = {"filled", "fallbackAccepted", "deferredWithBlocker"}
    assert {gap["status"] for gap in system["gapLedger"]} <= allowed_gap_status
    filled_gap_ids = {gap["id"] for gap in system["gapLedger"] if gap["status"] == "filled"}
    assert {
        "lifeCycleClassifier",
        "accountTraceAudit",
        "growthFeasibility",
        "narrativeMap",
        "storyToDrivers",
        "rdCapitalization",
        "leaseDebtAdjustment",
        "oneOffAdjustment",
        "peerMultipleDecomposition",
        "financialFirmExcessReturn",
        "sumOfParts",
        "distressAdjustedDcf",
    } <= filled_gap_ids
    engine_backlog = system["engineSupplementBacklog"]
    assert len(engine_backlog) >= 5
    assert {item["id"] for item in engine_backlog} >= {
        "storyboardSchemaBridge",
        "valuationMemoAdapter",
        "nonGenericFcffModelRouter",
        "industryPeerValuationPrimitive",
        "assumptionProvenanceSurface",
    }
    for item in engine_backlog:
        assert item["engineArea"]
        assert item["requiredBeforeEngineWork"]
        assert item["doNotImplementInSkillPhase"] is True
    assert system["dataContract"]["financialStatements"]["minimumPanelYears"] >= 5
    assert "peerValuation" in system["dataContract"]


def testDamodaranIndexIsEntrySkillForAnalysisSystem() -> None:
    index_text = (DAMODARAN_DIR / "index.md").read_text(encoding="utf-8")

    assert "entryHint: true" in index_text
    assert "Narrative & Numbers" in index_text
    assert "Business Life Cycle" in index_text
    assert "Financial Normalization" in index_text
    assert "Reverse DCF" in index_text
    assert "engineSupplementBacklog" in index_text
    assert "엔진 보강 후보" in index_text
    for skill_id in DAMODARAN_IDS - {"recipes.fundamental.valuation.damodaran.index"}:
        assert skill_id in index_text


def testDamodaranErpUpdaterTargetsReferenceData() -> None:
    # scripts/ 폴더 폐기 (CLAUDE.md noScriptsDir 룰) — .github/scripts/sync/ 로 이전.
    script = (REPO_ROOT / ".github" / "scripts" / "sync" / "updateDamodaranERP.py").read_text(encoding="utf-8")

    assert '"reference" / "data" / "damodaranDefaults.json"' in script
    assert '"core" / "data" / "damodaranDefaults.json"' not in script
