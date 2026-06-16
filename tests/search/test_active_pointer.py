"""Search active pointer resolution tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_active_index_dir_prefers_active_pointer(tmp_path, monkeypatch):
    import json

    import dartlab.config as cfg
    from dartlab.providers.dart.search import fieldIndex
    from dartlab.providers.dart.search.localUpdate import writeActivePointer

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    base = fieldIndex._contentIndexDir()
    (base / "main.npz").write_bytes(b"legacy")
    staged = base / "_staging" / "run1"
    staged.mkdir(parents=True)
    idx, meta = fieldIndex.buildContentSegment(
        [{"section_content": "active index", "rcept_no": "1", "section_order": 0}],
        showProgress=False,
    )
    fieldIndex.saveSegment(idx, meta, "main", outDir=staged)
    (staged / "manifest.json").write_text(
        json.dumps(
            {
                "artifactVersion": 1,
                "schemaVersion": fieldIndex.INDEX_SCHEMA_VERSION,
                "builtAt": "2026-06-15T00:00:00",
                "sourceDataAsOf": {"allFilings": "20260615"},
                "nDocsBySource": {"allFilings": 1},
                "requiredFiles": ["main.npz", "main_stems.json", "main_meta.parquet", "main_info.json"],
            }
        ),
        encoding="utf-8",
    )

    writeActivePointer(base, "_staging/run1")
    assert fieldIndex._activeIndexDir() == staged
