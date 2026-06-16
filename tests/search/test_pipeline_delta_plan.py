"""Search pipeline catalog delta dry-run tests."""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _manifest(source: str = "allFilings", *, totalRows: int = 2) -> dict:
    return {
        "source": source,
        "sourceVersion": "v1",
        "schemaVersion": "2026-06",
        "snapshotScope": "full",
        "dataAsOf": "20260615",
        "builtAt": "2026-06-15T00:00:00",
        "files": [{"path": f"{source}.parquet", "rowCount": totalRows}],
        "totalRows": totalRows,
        "changedRows": 1,
        "deletedRows": 0,
        "producer": "test",
    }


def test_plan_catalog_delta_uses_manifest_and_catalog_diff() -> None:
    from dartlab.providers.dart.search.pipeline import planCatalogDelta

    previous = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "allFilings", "rcept_no": "B", "text": "old"},
    ]
    current = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "allFilings", "rcept_no": "B", "text": "new"},
    ]
    result = planCatalogDelta(previous, current, [_manifest(totalRows=2)])
    assert result["valid"] is True
    assert result["delta"]["changedDocs"] == 1
    assert result["delta"]["unchangedDocs"] == 1
    assert result["shouldBuildDelta"] is True
    assert result["sourceDataAsOf"] == {"allFilings": "20260615"}


def test_plan_catalog_delta_rejects_source_count_drop() -> None:
    from dartlab.providers.dart.search.pipeline import planCatalogDelta

    result = planCatalogDelta([], [{"source": "allFilings", "rcept_no": "A", "text": "one"}], [_manifest(totalRows=10)])
    assert result["valid"] is False
    assert any(err.startswith("catalogSourceDrop:allFilings") for err in result["errors"])


def test_plan_catalog_delta_rejects_missing_expected_source() -> None:
    from dartlab.providers.dart.search.pipeline import planCatalogDelta

    result = planCatalogDelta(
        [],
        [{"source": "allFilings", "rcept_no": "A", "text": "one"}],
        [_manifest(totalRows=1)],
        expectedSources=["allFilings", "newsPublic"],
    )
    assert result["valid"] is False
    assert "sourceManifest:missingExpected:newsPublic" in result["errors"]


def test_plan_catalog_delta_rejects_empty_expected_source() -> None:
    from dartlab.providers.dart.search.pipeline import planCatalogDelta

    result = planCatalogDelta(
        [],
        [{"source": "allFilings", "rcept_no": "A", "text": "one"}],
        [_manifest(totalRows=0)],
        expectedSources=["allFilings"],
    )
    assert result["valid"] is False
    assert "sourceManifest:emptyExpected:allFilings" in result["errors"]


def test_plan_catalog_delta_rejects_partial_snapshot() -> None:
    from dartlab.providers.dart.search.pipeline import planCatalogDelta

    manifest = _manifest(totalRows=1)
    manifest["snapshotScope"] = "partial"
    result = planCatalogDelta([], [{"source": "allFilings", "rcept_no": "A", "text": "one"}], [manifest])
    assert result["valid"] is False
    assert "sourceManifest:partialSnapshot:allFilings" in result["errors"]


def test_run_catalog_delta_dry_run_writes_report(tmp_path) -> None:
    import polars as pl

    from dartlab.providers.dart.search.pipeline import runCatalogDeltaDryRun

    prev = tmp_path / "prev.parquet"
    curr = tmp_path / "curr.parquet"
    manifest = tmp_path / "source.json"
    report = tmp_path / "report.json"
    pl.DataFrame([{"source": "news", "url": "https://n.example/a", "title": "old"}]).write_parquet(prev)
    pl.DataFrame([{"source": "news", "url": "https://n.example/a", "title": "new"}]).write_parquet(curr)
    manifest.write_text(json.dumps(_manifest(source="newsPublic", totalRows=1)), encoding="utf-8")

    result = runCatalogDeltaDryRun(
        previousCatalogPath=prev,
        currentCatalogPath=curr,
        sourceManifestPaths=[manifest],
        reportPath=report,
    )
    assert result["valid"] is True
    assert report.exists()
    assert json.loads(report.read_text(encoding="utf-8"))["changedDocs"] == 1


def test_export_delta_rows_for_content_index_returns_new_and_changed() -> None:
    from dartlab.providers.dart.search.pipeline import exportDeltaRowsForContentIndex

    previous = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "news", "url": "https://n.example/a", "title": "old title"},
    ]
    current = [
        {"source": "allFilings", "rcept_no": "A", "text": "same"},
        {"source": "news", "url": "https://n.example/a", "title": "new title"},
        {"source": "edgar-panel", "accession": "0001", "text": "new filing"},
    ]
    rows = exportDeltaRowsForContentIndex(previous, current)
    assert rows.height == 2
    assert set(rows["source"].to_list()) == {"news", "edgar-panel"}
    assert set(rows["section_content"].to_list()) == {"new title", "new filing"}


def test_export_catalog_rows_for_content_index_skips_deleted() -> None:
    from dartlab.providers.dart.search.pipeline import exportCatalogRowsForContentIndex

    rows = exportCatalogRowsForContentIndex(
        [
            {"source": "allFilings", "rcept_no": "A", "text": "active"},
            {"source": "allFilings", "rcept_no": "B", "text": "gone", "deleted": True},
        ]
    )
    assert rows.height == 1
    assert rows["section_content"].to_list() == ["active"]
