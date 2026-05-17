"""AI audit helper scripts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_server_ask_audit():
    path = _REPO_ROOT / "scripts" / "audit" / "serverAskAudit.py"
    spec = importlib.util.spec_from_file_location("serverAskAudit", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_server_ask_audit_extracts_stream_artifacts():
    mod = _load_server_ask_audit()

    events = [
        {"event": "tool_call", "data": {"name": "gather"}},
        {
            "event": "tool_result",
            "data": {
                "artifacts": [
                    {"format": "csv", "url": "/api/ask/artifacts/2026-04-28/a.csv"},
                    {"format": "csv", "url": "/api/ask/artifacts/2026-04-28/a.csv"},
                ]
            },
        },
    ]

    artifacts = mod._artifactsFromEvents(events)

    assert len(artifacts) == 1
    assert artifacts[0]["format"] == "csv"


def test_server_ask_audit_requires_artifact_for_price_movers():
    mod = _load_server_ask_audit()

    assert mod._requiresCsvArtifact("q11_krx_movers", "최근 주가가 많이 오른 종목을 찾아줘")
    assert not mod._requiresCsvArtifact("q09_meta", "dartlab 뭐 할 수 있어?")


def test_server_ask_audit_compacts_stream_events():
    mod = _load_server_ask_audit()

    compact = mod._compactEvents(
        [
            {"event": "system_prompt", "data": {"text": "x" * 1000}},
            {
                "event": "tool_result",
                "data": {
                    "id": "call_1",
                    "name": "gather",
                    "result": "large-result",
                    "artifacts": [{"format": "csv", "primary": True, "url": "/a.csv"}],
                    "status": "ok",
                },
            },
        ]
    )

    assert len(compact) == 1
    assert compact[0]["data"]["resultChars"] == len("large-result")
    assert "result" not in compact[0]["data"]


def test_server_ask_audit_reads_done_response_meta_and_p95():
    mod = _load_server_ask_audit()

    events = [
        {"event": "done", "data": {"responseMeta": {"toolTotalMs": 10, "slowReason": ["story_tool_slow"]}}},
    ]

    assert mod._doneMeta(events)["toolTotalMs"] == 10
    assert mod._p95([1.0, 2.0, 100.0]) == 100.0


def test_server_ask_audit_compacts_refs_and_selected_skills():
    mod = _load_server_ask_audit()

    refs = [
        {
            "id": "skill:1",
            "kind": "skill",
            "source": "DartLabSkills",
            "payload": {"skillId": "engines.analysis.profitability", "score": 42.0},
        },
        {
            "id": "table:1",
            "kind": "table",
            "source": "run_python",
            "payload": {"metric": "op_margin", "rows": [{"year": "2025", "op_margin": 12.3}]},
        },
    ]

    assert mod._selectedSkillIds(refs) == ["engines.analysis.profitability"]
    compact = mod._compactRefs(refs)
    assert compact[1]["metric"] == "op_margin"
    assert compact[1]["rows"] == 1


def test_generate_spec_parses_ai_contract_block():
    path = _REPO_ROOT / "scripts" / "build" / "generateSpec.py"
    spec = importlib.util.spec_from_file_location("generateSpec", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    sections = mod._parseDocstringSections(
        """
        Summary.

        AIContract:
            contractId: demo.contract
            questionTypes: recent_price_mover, company_compare
            requiredEvidence: ["target", "metric"]
            freshness: {"cadence": "daily"}
            acceptanceCriteria: {"claimSupportRateMin": 0.9}
            failurePolicy: {"onMissingEvidence": "repair_once"}
        """
    )
    entry = {}
    mod._applyAiContract(entry, sections)

    assert entry["contractId"] == "demo.contract"
    assert entry["questionTypes"] == ["recent_price_mover", "company_compare"]
    assert entry["requiredEvidence"] == ["target", "metric"]
    assert entry["freshness"] == {"cadence": "daily"}
    assert entry["acceptanceCriteria"] == {"claimSupportRateMin": 0.9}
    assert entry["failurePolicy"] == {"onMissingEvidence": "repair_once"}


def test_analysis_graph_does_not_fallback_specific_gather_contract_to_any_gather():
    from dartlab.reference.capability.analysisGraph import contractForTool

    contract = contractForTool(
        "gather",
        {
            "axis": "sector",
            "target": "005930",
            "start": "2025-01-01",
            "end": "2025-12-31",
            "stockCodes": [],
        },
    )

    assert contract is None or contract.contractId != "gather.krx.close"
