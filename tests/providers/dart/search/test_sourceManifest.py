"""providers/dart/search/sourceManifest.py contract tests."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _manifest(**overrides):
    payload = {
        "source": "allFilings",
        "sourceVersion": "v1",
        "schemaVersion": "2026-06",
        "snapshotScope": "full",
        "dataAsOf": "20260615",
        "builtAt": "2026-06-15T00:00:00",
        "files": [{"path": "dart/allFilings/20260615.parquet", "rowCount": 1}],
        "totalRows": 1,
        "changedRows": 1,
        "deletedRows": 0,
        "producer": "originalSync.allfilings",
    }
    payload.update(overrides)
    return payload


def test_source_manifest_validation_accepts_known_source() -> None:
    from dartlab.providers.dart.search.sourceManifest import validateSourceManifest

    result = validateSourceManifest(_manifest(source="newsPublic"))
    assert result["valid"] is True
    assert result["source"] == "newsPublic"


def test_source_manifest_validation_rejects_missing_fields() -> None:
    from dartlab.providers.dart.search.sourceManifest import validateSourceManifest

    result = validateSourceManifest({"source": "allFilings"})
    assert result["valid"] is False
    assert "missing:dataAsOf" in result["errors"]


def test_source_manifest_validation_rejects_partial_scope_for_freshness() -> None:
    from dartlab.providers.dart.search.sourceManifest import sourceFreshness, validateSourceManifest

    partial = _manifest(snapshotScope="partial")
    result = validateSourceManifest(partial)
    assert result["valid"] is True
    assert sourceFreshness([partial]) == {}


def test_load_source_manifest_roundtrip(tmp_path) -> None:
    from dartlab.providers.dart.search.sourceManifest import loadSourceManifest, sourceFreshness

    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_manifest(source="edgarPanel", dataAsOf="20260614")), encoding="utf-8")
    loaded = loadSourceManifest(path)
    assert loaded is not None
    assert sourceFreshness([loaded]) == {"edgarPanel": "20260614"}
