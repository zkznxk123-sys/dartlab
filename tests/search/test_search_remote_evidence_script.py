"""Search remote evidence audit CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _writeJson(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_check_search_remote_evidence_script_with_complete_local_remote(tmp_path) -> None:
    remote = tmp_path / "remote"
    out = tmp_path / "remoteEvidence.json"
    for source in ("allFilings", "dartPanel"):
        _writeJson(
            remote / f"dart/searchCatalog/{source}/{source}.source_manifest.json",
            {
                "source": source,
                "snapshotScope": "full",
                "dataAsOf": "20260615",
                "builtAt": "2026-06-15T00:00:00",
                "files": [{"path": f"{source}.parquet", "rowCount": 1}],
                "totalRows": 1,
                "changedRows": 1,
                "deletedRows": 0,
                "producer": "test",
                "producerRun": _producerRun(source),
            },
        )
        (remote / f"dart/searchCatalog/{source}/{source}.catalog_snapshot.parquet").write_bytes(b"parquet")

    _writeJson(
        remote / "dart/contentIndex/manifest.json",
        {
            "artifactVersion": "search-content-index-v1",
            "schemaVersion": 2,
            "builtAt": "2026-06-15T00:00:00",
            "publishMode": "manifestPointer",
            "requiredFiles": ["main.npz", "source_manifest_set.json"],
            "fileSources": {
                "main.npz": "dart/contentIndex/_staging/run/main.npz",
                "source_manifest_set.json": "dart/contentIndex/_staging/run/source_manifest_set.json",
            },
            "sourceDataAsOf": {"allFilings": "20260615"},
            "nDocsBySource": {"allFilings": 1},
        },
    )
    (remote / "dart/contentIndex/_staging/run").mkdir(parents=True, exist_ok=True)
    (remote / "dart/contentIndex/_staging/run/main.npz").write_bytes(b"main")
    _writeJson(
        remote / "dart/contentIndex/_staging/run/source_manifest_set.json",
        {
            "schemaVersion": "searchSourceManifestSet.v1",
            "sourceManifestSetId": "manifest-set-1",
            "sources": [
                {"source": "allFilings", "producerRun": _producerRun("allFilings")},
                {"source": "dartPanel", "producerRun": _producerRun("dartPanel")},
            ],
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/checkSearchRemoteEvidence.py",
            "--remote-root",
            str(remote),
            "--expected-sources",
            "allFilings,dartPanel",
            "--content-tiers",
            "full",
            "--out",
            str(out),
            "--fail-on-missing",
        ],
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )

    assert proc.returncode == 0, proc.stderr + proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["sourceCatalog"]["missingSources"] == []
    assert report["sourceCatalog"]["sources"]["allFilings"]["manifest"]["totalRows"] == 1
    assert (
        report["sourceCatalog"]["sources"]["allFilings"]["manifest"]["producerRun"]["artifactName"]
        == "search-catalog-allFilings-allFilings-job-12345"
    )
    assert report["contentIndex"]["manifests"]["full"]["manifest"]["publishMode"] == "manifestPointer"
    assert report["contentIndex"]["manifests"]["full"]["manifest"]["sourceManifestSetSources"] == [
        "allFilings",
        "dartPanel",
    ]
    assert report["contentIndex"]["manifests"]["full"]["manifest"]["sourceManifestSetProducerRunMissingSources"] == []


def test_check_search_remote_evidence_script_reports_missing_file_sources(tmp_path) -> None:
    remote = tmp_path / "remote"
    out = tmp_path / "remoteEvidence.json"
    _writeJson(
        remote / "dart/contentIndex/manifest.json",
        {
            "artifactVersion": "search-content-index-v1",
            "schemaVersion": 2,
            "builtAt": "2026-06-15T00:00:00",
            "publishMode": "manifestPointer",
            "requiredFiles": ["main.npz"],
            "fileSources": {"main.npz": "dart/contentIndex/_staging/run/main.npz"},
            "sourceDataAsOf": {},
            "nDocsBySource": {},
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/checkSearchRemoteEvidence.py",
            "--remote-root",
            str(remote),
            "--expected-sources",
            "",
            "--content-tiers",
            "full",
            "--out",
            str(out),
            "--fail-on-missing",
        ],
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )

    assert proc.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "contentIndexFileSourceMissing" in report["blockers"]
    assert "missingContentFileSource:full:main.npz" in report["errors"]


def test_check_search_remote_evidence_script_reports_missing_blockers(tmp_path) -> None:
    remote = tmp_path / "remote"
    remote.mkdir()
    out = tmp_path / "remoteEvidence.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            ".github/scripts/search/checkSearchRemoteEvidence.py",
            "--remote-root",
            str(remote),
            "--expected-sources",
            "allFilings",
            "--content-tiers",
            "full,lite",
            "--out",
            str(out),
            "--fail-on-missing",
        ],
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
    )

    assert proc.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["valid"] is False
    assert "sourceCatalogMissing" in report["blockers"]
    assert "contentIndexManifestMissing" in report["blockers"]
    assert "missingSourceManifest:allFilings" in report["errors"]
    assert "missingContentManifest:lite" in report["errors"]


def _producerRun(source: str) -> dict[str, str]:
    return {
        "system": "githubActions",
        "workflow": "test workflow",
        "job": f"{source}-job",
        "runId": "12345",
        "runAttempt": "1",
        "sha": "abc123",
        "ref": "master",
        "artifactName": f"search-catalog-{source}-{source}-job-12345",
    }
