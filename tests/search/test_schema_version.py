"""검색 인덱스 schemaVersion 호환 계약 단위 테스트 — 코드↔HF 인덱스 버전 정합.

인덱스는 코드보다 자주 갱신된다. 받은 인덱스가 코드보다 신버전이면 indexInfo.compatible=False
로 표시(라이브러리 업그레이드 안내), 동버전 이하·legacy(미기록)는 호환. 네트워크 미사용.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _patch(monkeypatch, tmp_path):
    from dartlab.providers.dart.search import fieldIndex, fieldIndexRebuild

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda tier=None: tmp_path)
    monkeypatch.setattr(fieldIndex, "_activeIndexDir", lambda: tmp_path)
    monkeypatch.setattr(fieldIndexRebuild, "_HF_CONTENTINDEX_ATTEMPTED", True, raising=False)
    return fieldIndexRebuild


def test_schema_legacy_index_compatible(tmp_path, monkeypatch):
    """schemaVersion 미기록(legacy 인덱스) → version 0, compatible=True (best-effort 읽기)."""
    fir = _patch(monkeypatch, tmp_path)
    (tmp_path / "main_info.json").write_text(
        json.dumps({"nDocs": 100, "avgDocLength": 50.0, "builtAt": "2026-01-01T00:00:00"}), encoding="utf-8"
    )
    info = fir.indexInfo()
    assert info["available"] is True
    assert info["schemaVersion"] == 0
    assert info["compatible"] is True


def test_schema_future_index_incompatible(tmp_path, monkeypatch):
    """인덱스 schemaVersion 이 코드보다 신버전 → compatible=False (라이브러리 업그레이드 필요)."""
    from dartlab.providers.dart.search.fieldIndex import INDEX_SCHEMA_VERSION

    fir = _patch(monkeypatch, tmp_path)
    (tmp_path / "main_info.json").write_text(
        json.dumps(
            {
                "nDocs": 100,
                "avgDocLength": 50.0,
                "builtAt": "2099-01-01T00:00:00",
                "schemaVersion": INDEX_SCHEMA_VERSION + 1,
            }
        ),
        encoding="utf-8",
    )
    info = fir.indexInfo()
    assert info["schemaVersion"] == INDEX_SCHEMA_VERSION + 1
    assert info["compatible"] is False


def test_schema_same_version_compatible(tmp_path, monkeypatch):
    """동버전 인덱스 → compatible=True."""
    from dartlab.providers.dart.search.fieldIndex import INDEX_SCHEMA_VERSION

    fir = _patch(monkeypatch, tmp_path)
    (tmp_path / "main_info.json").write_text(
        json.dumps(
            {
                "nDocs": 100,
                "avgDocLength": 50.0,
                "builtAt": "2026-06-01T00:00:00",
                "schemaVersion": INDEX_SCHEMA_VERSION,
            }
        ),
        encoding="utf-8",
    )
    info = fir.indexInfo()
    assert info["compatible"] is True
