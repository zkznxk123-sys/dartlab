"""Search active pointer resolution tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_active_index_dir_prefers_active_pointer(tmp_path, monkeypatch):
    import dartlab.config as cfg
    from dartlab.providers.dart.search import fieldIndex
    from dartlab.providers.dart.search.fieldIndexRebuild import writeIndexManifest
    from dartlab.providers.dart.search.localUpdate import writeActivePointer

    monkeypatch.setattr(cfg, "dataDir", str(tmp_path))
    base = fieldIndex._contentIndexDir()
    (base / "main.postings.bin").write_bytes(b"flat-decoy")  # flat 후보 — 활성 포인터가 우선함을 입증
    staged = base / "_staging" / "run1"
    staged.mkdir(parents=True)
    idx, meta = fieldIndex.buildContentSegment(
        [{"section_content": "active index", "rcept_no": "1", "section_order": 0}],
        showProgress=False,
    )
    fieldIndex.saveSegmentWithSidecar(idx, meta, "main", staged)  # 동반물 + sidecar(=SSOT)
    writeIndexManifest(staged, tier="full", buildCommand="test.activePointer")  # 실제 requiredFiles(sidecar)

    writeActivePointer(base, "_staging/run1")
    assert fieldIndex._activeIndexDir() == staged
