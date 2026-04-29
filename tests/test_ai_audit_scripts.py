"""AI audit helper scripts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_server_ask_audit():
    path = Path("scripts/audit/serverAskAudit.py")
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


def test_generate_spec_parses_ai_contract_block():
    path = Path("scripts/build/generateSpec.py")
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
        """
    )
    entry = {}
    mod._applyAiContract(entry, sections)

    assert entry["contractId"] == "demo.contract"
    assert entry["questionTypes"] == ["recent_price_mover", "company_compare"]
    assert entry["requiredEvidence"] == ["target", "metric"]
    assert entry["freshness"] == {"cadence": "daily"}
