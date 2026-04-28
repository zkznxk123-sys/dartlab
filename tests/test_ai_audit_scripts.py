"""AI audit helper scripts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _load_server_ask_audit():
    path = Path("scripts/audit/serverAskAudit.py")
    spec = importlib.util.spec_from_file_location("serverAskAudit", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
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
