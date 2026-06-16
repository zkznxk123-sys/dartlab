"""Search freshness repair script tests."""

from __future__ import annotations

import json
from importlib import util
from pathlib import Path

import polars as pl


def _loadRepairScript():
    path = Path(".github/scripts/search/repairSearchFreshness.py")
    spec = util.spec_from_file_location("repairSearchFreshnessScript", path)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repair_search_freshness_updates_catalogs_content_manifest_and_hashes(tmp_path) -> None:
    module = _loadRepairScript()
    catalogDir = tmp_path / "searchCatalog"
    contentDir = tmp_path / "contentIndex"
    _writeSource(
        catalogDir,
        "dartPanel",
        dataAsOf="20261231",
        rows=[
            {
                "docKey": "dart:panel:1#section=0",
                "source": "dartPanel",
                "sourceRef": "dart:panel:1#section=0",
                "sourcePriority": 10,
                "rceptNo": "20260615000001",
                "accession": "",
                "urlHash": "",
                "url": "",
                "sectionKey": "0",
                "sectionOrder": 0,
                "corpCode": "",
                "stockCode": "005930",
                "ticker": "",
                "companyName": "삼성전자",
                "date": "20260615",
                "reportName": "",
                "title": "",
                "searchText": "본문",
                "textHash": "t1",
                "metadataHash": "m1",
                "contentLen": 2,
                "deleted": False,
                "sourceDataAsOf": "20260615",
                "sourceAdapterVersion": "v1",
            }
        ],
    )
    _writeSource(
        catalogDir,
        "edgarPanel",
        dataAsOf="20260630",
        rows=[
            {
                "docKey": "edgar:panel:a#section=0",
                "source": "edgarPanel",
                "sourceRef": "edgar:panel:a#section=0",
                "sourcePriority": 10,
                "rceptNo": "a",
                "accession": "a",
                "urlHash": "",
                "url": "",
                "sectionKey": "0",
                "sectionOrder": 0,
                "corpCode": "",
                "stockCode": "",
                "ticker": "AAPL",
                "companyName": "AAPL",
                "date": "20260630",
                "reportName": "",
                "title": "10-Q",
                "searchText": "risk",
                "textHash": "t2",
                "metadataHash": "m2",
                "contentLen": 4,
                "deleted": False,
                "sourceDataAsOf": "20260630",
                "sourceAdapterVersion": "v1",
            }
        ],
    )
    pl.concat(
        [
            pl.read_parquet(catalogDir / "dartPanel" / "dartPanel.catalog_snapshot.parquet"),
            pl.read_parquet(catalogDir / "edgarPanel" / "edgarPanel.catalog_snapshot.parquet"),
        ]
    ).write_parquet(catalogDir / "main.current.catalog_snapshot.parquet")
    (catalogDir / "source_manifest_set.json").write_text(
        json.dumps(
            {
                "schemaVersion": "searchSourceManifestSet.v1",
                "expectedSources": ["dartPanel", "edgarPanel"],
                "combinedCatalogSha256": "old",
                "combinedCatalogRows": 2,
                "sourceManifestSetId": "old",
                "sources": [],
            }
        ),
        encoding="utf-8",
    )

    contentDir.mkdir(parents=True)
    pl.DataFrame(
        [
            {"source": "edgar-panel", "sourceDataAsOf": "20260630", "rcept_no": "a"},
            {"source": "panel", "sourceDataAsOf": "20260615", "rcept_no": "1"},
        ]
    ).write_parquet(contentDir / "main_meta.parquet")
    (contentDir / "source_manifest_set.json").write_text("{}", encoding="utf-8")
    (contentDir / "manifest.json").write_text(
        json.dumps(
            {
                "artifactVersion": 1,
                "schemaVersion": 2,
                "builtAt": "2026-06-16T00:00:00",
                "mainDataAsOf": "20260630",
                "sourceDataAsOf": {"edgar-panel": "20260630", "panel": "20260615"},
                "nDocsBySource": {"edgar-panel": 1, "panel": 1},
                "requiredFiles": ["main_meta.parquet", "source_manifest_set.json"],
                "fileHashes": {},
            }
        ),
        encoding="utf-8",
    )

    summary = module.repairFreshnessArtifacts(
        catalogDir,
        [contentDir],
        sourceFallbacks={"edgarPanel": "20260616"},
    )

    assert summary["valid"] is True
    dartManifest = json.loads((catalogDir / "dartPanel" / "dartPanel.source_manifest.json").read_text())
    edgarManifest = json.loads((catalogDir / "edgarPanel" / "edgarPanel.source_manifest.json").read_text())
    assert dartManifest["dataAsOf"] == "20260615"
    assert edgarManifest["dataAsOf"] == "20260616"
    edgarCatalog = pl.read_parquet(catalogDir / "edgarPanel" / "edgarPanel.catalog_snapshot.parquet")
    assert edgarCatalog.row(0, named=True)["date"] == "20260630"
    assert edgarCatalog.row(0, named=True)["sourceDataAsOf"] == "20260616"

    manifestSet = json.loads((catalogDir / "source_manifest_set.json").read_text())
    assert manifestSet["sourceManifestSetId"] != "old"
    assert {row["source"]: row["dataAsOf"] for row in manifestSet["sources"]} == {
        "dartPanel": "20260615",
        "edgarPanel": "20260616",
    }
    contentManifestSet = json.loads((contentDir / "source_manifest_set.json").read_text())
    assert contentManifestSet["sourceManifestSetId"] == manifestSet["sourceManifestSetId"]

    manifest = json.loads((contentDir / "manifest.json").read_text())
    assert manifest["sourceDataAsOf"]["edgar-panel"] == "20260616"
    assert manifest["mainDataAsOf"] == "20260616"
    assert manifest["sourceManifestSetId"] == manifestSet["sourceManifestSetId"]
    assert set(manifest["fileHashes"]) == {"main_meta.parquet", "source_manifest_set.json"}
    assert manifest["fileHashes"]["main_meta.parquet"] == module._sha256File(contentDir / "main_meta.parquet")


def test_parse_source_fallbacks_accepts_index_source_alias() -> None:
    module = _loadRepairScript()

    assert module.parseSourceFallbacks(["edgar-panel=2026-06-16", "panel=20260615"]) == {
        "edgarPanel": "20260616",
        "dartPanel": "20260615",
    }


def _writeSource(catalogDir: Path, source: str, *, dataAsOf: str, rows: list[dict]) -> None:
    sourceDir = catalogDir / source
    sourceDir.mkdir(parents=True)
    catalogPath = sourceDir / f"{source}.catalog_snapshot.parquet"
    pl.DataFrame(rows).write_parquet(catalogPath)
    (sourceDir / f"{source}.source_manifest.json").write_text(
        json.dumps(
            {
                "source": source,
                "snapshotScope": "full",
                "dataAsOf": dataAsOf,
                "builtAt": "2026-06-16T00:00:00",
                "files": [{"path": f"{source}.parquet", "rowCount": len(rows)}],
                "totalRows": len(rows),
                "changedRows": len(rows),
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
