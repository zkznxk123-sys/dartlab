"""Event radar incubator recipe guard tests."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import polars as pl
import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
EVENT_RADAR_DIR = REPO_ROOT / "src" / "dartlab" / "skills" / "specs" / "recipes" / "incubator" / "eventRadar"

EVENT_RADAR_IDS = {
    "recipes.incubator.eventRadar.index",
    "recipes.incubator.eventRadar.sourceCoverageAudit",
    "recipes.incubator.eventRadar.eventInbox",
    "recipes.incubator.eventRadar.priceFlowReaction",
    "recipes.incubator.eventRadar.insiderOwnershipSignal",
    "recipes.incubator.eventRadar.capitalActionMonitor",
    "recipes.incubator.eventRadar.consensusDriftWatch",
    "recipes.incubator.eventRadar.falsifierLedger",
    "recipes.incubator.eventRadar.engineCandidateMemo",
    "recipes.incubator.eventRadar.visualDecisionPack",
    "recipes.incubator.eventRadar.deepDive",
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


def testEventRadarRecipeSpecsLoadAsObservedRecipes() -> None:
    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    specs = {spec.id: spec for spec in listSkills(includeUser=False)}

    assert EVENT_RADAR_IDS <= set(specs)
    for skill_id in EVENT_RADAR_IDS:
        spec = specs[skill_id]
        assert spec.kind == "recipe"
        assert spec.category == "recipes"
        assert spec.status == "observed"
        assert spec.graphTier == "L1.5"
        assert spec.requiredEvidence
        assert spec.expectedOutputs
        assert set(spec.capabilityRefs) & {
            "Company.disclosure",
            "Company.liveFilings",
            "Company.gather",
            "scan.market",
            "scan.insider",
            "scan.capital",
        }


def testEventRadarSkillsAreExposedThroughAiEntryPoints() -> None:
    from dartlab.ai.tools.readSkill import getSkillBody, readSkill

    entry = readSkill("이벤트 레이더 eventRadar incubator 촉매 체크", limit=8, includeUser=False)
    reaction = readSkill("price flow reaction 이벤트 주가 수급 반응", limit=8, includeUser=False)
    visual = readSkill("visual decision pack observed viz priceChart kpiRibbon", limit=8, includeUser=False)

    assert entry.ok
    assert entry.data["skills"][0]["id"] == "recipes.incubator.eventRadar.index"
    assert reaction.ok
    assert reaction.data["skills"][0]["id"] == "recipes.incubator.eventRadar.priceFlowReaction"
    assert visual.ok
    assert visual.data["skills"][0]["id"] == "recipes.incubator.eventRadar.visualDecisionPack"

    body = getSkillBody("recipes.incubator.eventRadar.deepDive", includeUser=False)
    assert body.ok
    raw = body.data["body"]
    assert "buildEventRadarMemo" in raw
    assert "recipes.incubator.eventRadar.visualDecisionPack" in raw


def testEventRadarSkillsAreInPublicSkillArtifacts() -> None:
    artifact_dir = REPO_ROOT / "src" / "dartlab" / "skills"

    for name in ("index.json", "agent.json", "web.json", "mcp.json", "pyodide.json"):
        payload = json.loads((artifact_dir / name).read_text(encoding="utf-8"))
        rows = payload.get("skills", [])
        by_id = {row["id"]: row for row in rows}

        assert EVENT_RADAR_IDS <= set(by_id), f"{name} missing event radar skill rows"
        if name != "pyodide.json":
            assert payload["meta"]["skillCount"] == len(rows)
            recipe_meta = [row for row in payload["meta"]["categories"] if row["id"] == "recipes"]
            assert recipe_meta and recipe_meta[0]["count"] == sum(row.get("category") == "recipes" for row in rows)
        if name in {"index.json", "agent.json", "mcp.json"}:
            assert by_id["recipes.incubator.eventRadar.index"]["bodyPreview"]
        if name in {"index.json", "agent.json", "web.json"}:
            assert by_id["recipes.incubator.eventRadar.deepDive"]["expectedOutputs"]
        if name == "web.json":
            assert by_id["recipes.incubator.eventRadar.index"]["bodyHuman"]

    graph = json.loads((artifact_dir / "graph.json").read_text(encoding="utf-8"))
    graph_ids = {node["id"] for node in graph.get("nodes", [])}
    assert EVENT_RADAR_IDS <= graph_ids


def testEventRadarPublicCallBlocksStayBelowL2() -> None:
    failures: list[str] = []
    for path in sorted(EVENT_RADAR_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        for token in BANNED_L2_CALLS:
            if token in section:
                failures.append(f"{path.name}: banned L2 call {token}")

    assert not failures, "Event radar recipes must not call L2 engines\n" + "\n".join(failures)


def testEventRadarPublicCallBlocksParseAsPython() -> None:
    failures: list[str] = []
    for path in sorted(EVENT_RADAR_DIR.glob("*.md")):
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

    assert not failures, "Event radar recipe code blocks must be AST-parseable\n" + "\n".join(failures)


def testEventRadarPublicCallBlocksUseL15MemoBuilder() -> None:
    failures: list[str] = []
    for path in sorted(EVENT_RADAR_DIR.glob("*.md")):
        section = _publicCallSection(path.read_text(encoding="utf-8"))
        if 'target = "005930"' not in section:
            failures.append(f"{path.name}: missing default target placeholder")
        if "buildEventRadarMemo" not in section:
            failures.append(f"{path.name}: missing L1.5 memo builder")
        if 'sources=memo["sources"]' not in section:
            failures.append(f"{path.name}: missing sourceRef payload")

    assert not failures, "Event radar recipes must execute the L1.5 helper\n" + "\n".join(failures)


def testEventRadarVisualRefsUseObservedVizSkillsOnly() -> None:
    from dartlab.skills import listSkills
    from dartlab.skills import registry as _registry

    _registry._LIST_SKILLS_CACHE.clear()
    specs = {spec.id: spec for spec in listSkills(includeUser=False)}

    for skill_id in EVENT_RADAR_IDS:
        spec = specs[skill_id]
        for visual_ref in spec.visualRefs:
            assert visual_ref.startswith("engines.viz.")
            assert specs[visual_ref].status == "observed"


def testEventRadarSynthBuildsDeepMemoFromL15Inputs() -> None:
    from dartlab.synth.eventRadar import buildEventRadarMemo

    memo = buildEventRadarMemo(
        target="SAMPLE",
        market="KR",
        companyName="Sample Battery",
        filings=[
            {"rcept_dt": "20260510", "report_nm": "전환사채 발행 결정"},
            {"rcept_dt": "20260508", "report_nm": "자기주식취득 신탁계약 체결 결정"},
            {"rcept_dt": "20260501", "report_nm": "분기보고서 정정 공시"},
        ],
        newsRows=[{"date": "2026-05-11", "title": "Sample Battery earnings guidance revised"}],
        priceRows=pl.DataFrame(
            [
                {"date": "2026-05-11", "close": 118000.0, "volume": 4200000.0},
                {"date": "2026-05-10", "close": 105000.0, "volume": 1100000.0},
            ]
        ),
        flowRows=[{"date": "2026-05-11", "foreignNetBuy": 12_000_000.0, "institutionNetBuy": 8_000_000.0}],
        insiderRows=[{"date": "2026-05-09", "name": "CFO", "transaction": "buy", "amount": 1500.0}],
        ownershipRows=[{"date": "2026-05-09", "holder": "Major Holder", "changePct": 1.4}],
        dividendRows=[{"date": "2026-05-07", "dps": 1200.0}],
        splitRows=[{"date": "2026-05-06", "ratio": "2:1"}],
        consensusRows=[
            {
                "date": "2026-05-11",
                "revenueConsensus": 900.0,
                "opConsensus": 120.0,
                "epsConsensus": 3100.0,
                "targetPrice": 140000.0,
            },
            {
                "date": "2026-04-25",
                "revenueConsensus": 1000.0,
                "opConsensus": 150.0,
                "epsConsensus": 3600.0,
                "targetPrice": 150000.0,
            },
        ],
        scanRows=[
            {"target": "SAMPLE", "axis": "market", "score": 2.0},
            {"target": "SAMPLE", "axis": "insider", "score": 1.0},
        ],
    )

    assert memo["decisionStatus"] == "usable"
    assert memo["headline"]["radarScore"] >= 8
    assert memo["headline"]["eventCount"] == 4
    assert memo["headline"]["openFalsifierCount"] >= 4
    assert {
        "sourceCoverageAudit",
        "eventInbox",
        "priceFlowReaction",
        "insiderOwnershipSignal",
        "capitalActionMonitor",
        "consensusDriftWatch",
        "scanContext",
        "falsifierLedger",
        "engineCandidateMemo",
        "visualDecisionPack",
        "deepDive",
    } <= set(memo["tables"])
    assert len(memo["tables"]["deepDive"]) == 11
    assert memo["tables"]["deepDive"][-1]["step"] == "finalDecision"
    assert memo["tables"]["priceFlowReaction"][0]["status"] == "risk"
    assert any(row["category"] == "financing" and row["status"] == "risk" for row in memo["tables"]["eventInbox"])
    assert any(
        row["claim"] == "price/flow reaction" and row["status"] == "open" for row in memo["tables"]["falsifierLedger"]
    )
    assert any(row["signalId"] == "priceFlowReaction" for row in memo["tables"]["engineCandidateMemo"])
    assert all(row["status"] == "ready" for row in memo["tables"]["visualDecisionPack"])
    assert any(source["id"] == "l15EventRadar" for source in memo["sources"])
