"""Search catalog changed-set diff tests."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_normalize_catalog_rows_builds_stable_source_refs() -> None:
    from dartlab.providers.dart.search.catalog import normalizeCatalogRows

    rows = normalizeCatalogRows(
        [
            {"source": "allFilings", "rcept_no": "20260615000001", "section_order": 2, "text": "유상증자"},
            {"source": "panel", "rcept_no": "20260615000001", "section_order": 0, "text": "정기보고서"},
            {"source": "edgar-panel", "accession": "0001090872-15-000032", "text": "revenue"},
            {"source": "news", "url": "https://n.example/a", "title": "기사"},
        ]
    )
    refs = set(rows["sourceRef"].to_list())
    assert "dart:allFilings:20260615000001#section=2" in refs
    assert "dart:panel:20260615000001#section=0" in refs
    assert "edgar:panel:0001090872-15-000032#section=0" in refs
    assert any(ref.startswith("news:") for ref in refs)
    assert "searchText" in rows.columns


def test_diff_catalog_classifies_new_changed_deleted_unchanged() -> None:
    from dartlab.providers.dart.search.catalog import diffCatalog

    previous = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "panel", "rcept_no": "B", "text": "old"},
        {"source": "news", "url": "https://n.example/old", "title": "old news"},
    ]
    current = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "panel", "rcept_no": "B", "text": "new"},
        {"source": "edgar-panel", "accession": "C", "text": "new edgar"},
    ]
    delta = diffCatalog(previous, current)
    assert delta.summary == {
        "newDocs": 1,
        "changedDocs": 1,
        "deletedDocs": 1,
        "unchangedDocs": 1,
        "totalCurrentDocs": 3,
        "totalPreviousDocs": 3,
    }
    assert delta.new.row(0, named=True)["source"] == "edgarPanel"
    assert delta.changed.row(0, named=True)["source"] == "dartPanel"
    assert delta.deleted.row(0, named=True)["deleted"] is True
