"""Search product manifest indexInfo contract tests."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _patch(monkeypatch, tmp_path):
    from dartlab.providers.dart.search import fieldIndex, fieldIndexRebuild

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda tier=None: tmp_path)
    monkeypatch.setattr(fieldIndex, "_activeIndexDir", lambda: tmp_path)
    monkeypatch.setattr(fieldIndexRebuild, "_HF_CONTENTINDEX_ATTEMPTED", True, raising=False)
    return fieldIndex, fieldIndexRebuild


def test_index_info_reads_product_manifest(tmp_path, monkeypatch):
    from dartlab.providers.dart.search.fieldIndex import INDEX_SCHEMA_VERSION

    _, fir = _patch(monkeypatch, tmp_path)
    (tmp_path / "main.npz").write_bytes(b"idx")
    manifest = {
        "artifactVersion": 1,
        "schemaVersion": INDEX_SCHEMA_VERSION,
        "builtAt": "2026-06-15T01:00:00",
        "mainDataAsOf": "20260614",
        "deltaDataAsOf": "20260615",
        "sourceDataAsOf": {"allFilings": "20260615", "newsPublic": "20260615"},
        "nDocsBySource": {"allFilings": 10, "news": 3},
        "nDocsByTier": {"full": 13},
        "requiredFiles": ["main.npz"],
        "hasDelta": True,
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    info = fir.indexInfo()
    assert info["available"] is True
    assert info["dataAsOf"] == "20260615"
    assert info["nDocs"] == 13
    assert info["sourceDataAsOf"]["allFilings"] == "20260615"
    assert info["nDocsBySource"]["news"] == 3
    assert info["hasDelta"] is True
    assert info["manifestValid"] is True


def test_index_info_manifest_missing_required_file_not_available(tmp_path, monkeypatch):
    from dartlab.providers.dart.search.fieldIndex import INDEX_SCHEMA_VERSION

    _, fir = _patch(monkeypatch, tmp_path)
    manifest = {
        "artifactVersion": 1,
        "schemaVersion": INDEX_SCHEMA_VERSION,
        "builtAt": "2026-06-15T01:00:00",
        "sourceDataAsOf": {"allFilings": "20260615"},
        "nDocsBySource": {"allFilings": 10},
        "requiredFiles": ["main.npz"],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    info = fir.indexInfo()
    assert info["available"] is False
    assert info["manifestValid"] is False
    assert "missingFile:main.npz" in info["manifestErrors"]


def test_top_level_search_exposes_index_info(monkeypatch) -> None:
    import dartlab
    from dartlab.providers.dart.search import api

    monkeypatch.setattr(api, "indexInfo", lambda: {"available": True, "nDocs": 3})

    assert dartlab.search.indexInfo()["nDocs"] == 3


def test_top_level_search_exposes_prefetch(monkeypatch) -> None:
    import dartlab
    from dartlab.providers.dart.search import api

    monkeypatch.setattr(api, "prefetch", lambda tier=None: {"tier": tier or "lite"})

    assert dartlab.search.prefetch(tier="full")["tier"] == "full"
