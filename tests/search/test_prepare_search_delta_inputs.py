"""prepareSearchDeltaInputs script tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import polars as pl


def test_prepare_search_delta_inputs_writes_env(tmp_path) -> None:
    sourceDir = tmp_path / "searchCatalog" / "allFilings"
    sourceDir.mkdir(parents=True)
    (sourceDir / "allFilings.source_manifest.json").write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
                "producerRun": {
                    "system": "githubActions",
                    "workflow": "Original SSOT Sync",
                    "job": "allfilings",
                    "runId": "12345",
                    "sha": "abc123",
                    "artifactName": "search-catalog-allFilings-allfilings-12345",
                },
            }
        ),
        encoding="utf-8",
    )
    pl.DataFrame([{"source": "allFilings", "sourceRef": "dart:x", "searchText": "x"}]).write_parquet(
        sourceDir / "allFilings.catalog_snapshot.parquet"
    )
    envFile = tmp_path / "env.txt"
    current = tmp_path / "current.parquet"
    manifestSet = tmp_path / "source_manifest_set.json"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/prepareSearchDeltaInputs.py",
            "--source-dir",
            str(tmp_path / "searchCatalog"),
            "--out-current",
            str(current),
            "--out-manifest-set",
            str(manifestSet),
            "--env-file",
            str(envFile),
            "--expected-sources",
            "allFilings",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert current.exists()
    text = envFile.read_text(encoding="utf-8")
    assert "DARTLAB_SEARCH_DELTA_MODE=catalog" in text
    assert "DARTLAB_SEARCH_MAIN_MODE=catalog" in text
    assert "DARTLAB_SEARCH_CURRENT_CATALOG=" in text
    assert "DARTLAB_SEARCH_SOURCE_MANIFEST_SET=" in text
    payload = json.loads(manifestSet.read_text(encoding="utf-8"))
    assert payload["sourceManifestSetId"]
    assert payload["combinedCatalogRows"] == 1
    assert payload["sources"][0]["source"] == "allFilings"
    assert payload["sources"][0]["catalogRows"] == 1
    assert payload["sources"][0]["producerRun"]["runId"] == "12345"


def test_prepare_search_delta_inputs_keeps_legacy_when_expected_source_missing(tmp_path) -> None:
    sourceDir = tmp_path / "searchCatalog" / "allFilings"
    sourceDir.mkdir(parents=True)
    (sourceDir / "allFilings.source_manifest.json").write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
    pl.DataFrame([{"source": "allFilings", "sourceRef": "dart:x", "searchText": "x"}]).write_parquet(
        sourceDir / "allFilings.catalog_snapshot.parquet"
    )
    envFile = tmp_path / "env.txt"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/prepareSearchDeltaInputs.py",
            "--source-dir",
            str(tmp_path / "searchCatalog"),
            "--env-file",
            str(envFile),
            "--expected-sources",
            "allFilings,newsPublic",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "expected source catalogs missing: newsPublic" in proc.stdout
    assert not envFile.exists()


def test_prepare_search_delta_inputs_requires_previous_catalog_for_delta(tmp_path) -> None:
    sourceDir = tmp_path / "searchCatalog" / "allFilings"
    sourceDir.mkdir(parents=True)
    (sourceDir / "allFilings.source_manifest.json").write_text(
        json.dumps(
            {
                "source": "allFilings",
                "sourceVersion": "v1",
                "schemaVersion": "2026-06",
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
            }
        ),
        encoding="utf-8",
    )
    pl.DataFrame([{"source": "allFilings", "sourceRef": "dart:x", "searchText": "x"}]).write_parquet(
        sourceDir / "allFilings.catalog_snapshot.parquet"
    )
    envFile = tmp_path / "env.txt"
    current = tmp_path / "current.parquet"
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/prepareSearchDeltaInputs.py",
            "--source-dir",
            str(tmp_path / "searchCatalog"),
            "--previous",
            str(tmp_path / "missing.previous.parquet"),
            "--out-current",
            str(current),
            "--env-file",
            str(envFile),
            "--expected-sources",
            "allFilings",
            "--require-previous-catalog",
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert "previous catalog missing" in proc.stdout
    assert not current.exists()
    assert not envFile.exists()


def test_prepare_search_delta_inputs_noops_without_artifacts(tmp_path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/prepareSearchDeltaInputs.py",
            "--source-dir",
            str(tmp_path / "missing"),
            "--env-file",
            "",
        ],
        cwd=Path.cwd(),
        env={**os.environ, "GITHUB_ENV": ""},
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "keep legacy delta mode" in proc.stdout
