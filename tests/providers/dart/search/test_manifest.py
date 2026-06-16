"""providers/dart/search/manifest.py mirror tests."""

from __future__ import annotations

import hashlib

import pytest

pytestmark = pytest.mark.unit


def test_import() -> None:
    import dartlab.providers.dart.search.manifest as mod

    assert mod is not None


def test_manifest_validation_checks_required_files(tmp_path) -> None:
    from dartlab.providers.dart.search.manifest import validateSearchManifest

    (tmp_path / "main.npz").write_bytes(b"idx")
    payload = {
        "artifactVersion": 1,
        "schemaVersion": 2,
        "builtAt": "2026-06-15T00:00:00",
        "sourceDataAsOf": {"allFilings": "20260615"},
        "nDocsBySource": {"allFilings": 10},
        "requiredFiles": ["main.npz", "main_info.json"],
    }
    result = validateSearchManifest(payload, tmp_path)
    assert result["valid"] is False
    assert "missingFile:main_info.json" in result["errors"]


def test_manifest_validation_checks_hash(tmp_path) -> None:
    from dartlab.providers.dart.search.manifest import validateSearchManifest

    content = b"ok"
    (tmp_path / "main_info.json").write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    payload = {
        "artifactVersion": 1,
        "schemaVersion": 2,
        "builtAt": "2026-06-15T00:00:00",
        "sourceDataAsOf": {"allFilings": "20260615"},
        "nDocsBySource": {"allFilings": 10},
        "requiredFiles": ["main_info.json"],
        "fileHashes": {"main_info.json": digest},
    }
    result = validateSearchManifest(payload, tmp_path)
    assert result["valid"] is True
    assert result["checkedFiles"] == 1


def test_manifest_validation_rejects_incompatible_schema(tmp_path) -> None:
    from dartlab.providers.dart.search.manifest import validateSearchManifest

    payload = {
        "artifactVersion": 1,
        "schemaVersion": 99,
        "builtAt": "2026-06-15T00:00:00",
        "sourceDataAsOf": {"allFilings": "20260615"},
        "nDocsBySource": {"allFilings": 10},
        "requiredFiles": [],
    }
    result = validateSearchManifest(payload, tmp_path, codeSchemaVersion=1)
    assert result["valid"] is False
    assert "schemaIncompatible:99:1:1" in result["errors"]
