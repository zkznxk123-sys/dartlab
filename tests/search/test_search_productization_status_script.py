"""Search productization status CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(".github/scripts/search/evaluateSearchProductizationStatus.py")


def test_productization_status_blocks_missing_remote_evidence(tmp_path: Path) -> None:
    localInfo = tmp_path / "indexInfo.json"
    localInfo.write_text(
        json.dumps(
            {
                "available": True,
                "compatible": True,
                "manifestValid": True,
                "nDocs": 10,
                "nDocsBySource": {"allFilings": 10},
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(tmp_path / "missing-remote"),
            "--local-index-info",
            str(localInfo),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["designReady"] is True
    assert report["opsReady"] is False
    assert "sourceCatalogMissing" in report["blockers"]
    assert "contentIndexManifestMissing" in report["blockers"]


def test_productization_status_accepts_complete_evidence_bundle(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    localInfo = _writeJson(
        tmp_path / "indexInfo.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(tmp_path / "resultContract.json", {"valid": True, "totalRows": 30, "invalidRows": []})
    canary = _writeJson(
        tmp_path / "canary.json",
        {
            "valid": True,
            "totalRows": 4,
            "passedRows": 4,
            "failures": [],
            "rows": [
                {"query": "공시 원문", "expectedSource": "allFilings", "passed": True},
                {"query": "공시 원문 분기보고서", "expectedSource": "panel", "passed": True},
                {"query": "edgar filing", "expectedSource": "edgar-panel", "passed": True},
                {"query": "뉴스 기사", "expectedSource": "news", "passed": True},
            ],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    quality = _writeJson(
        tmp_path / "quality.json",
        {
            "releaseEligible": True,
            "totalRows": 120,
            "realReviewedRows": 120,
            "coverageByKind": {"filing": 50, "news": 30, "noAnswer": 20, "edgar": 20},
            "goldOriginCounts": {"userLog": 120},
            "reviewStatusCounts": {"reviewed": 120},
            "metrics": {"overallReadyRate": 0.95},
            "blockers": [],
        },
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(localInfo),
            "--result-contract",
            str(resultContract),
            "--canary-report",
            str(canary),
            "--hf-round-trip",
            str(roundTripFull),
            "--hf-round-trip",
            str(roundTripLite),
            "--quality-report",
            str(quality),
            "--out",
            str(out),
            "--fail-on-release-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["opsReady"] is True
    assert report["releaseReady"] is True
    assert report["blockers"] == []


def test_productization_status_revalidates_quality_report_counts(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    aux = _writeCompleteAuxEvidence(tmp_path)
    spoofedQuality = _writeJson(
        tmp_path / "spoofedQuality.json",
        {
            "releaseEligible": True,
            "totalRows": 120,
            "coverageByKind": {"filing": 120},
            "goldOriginCounts": {"drillSynthetic": 120},
            "reviewStatusCounts": {"drillReviewed": 120},
            "blockers": [],
        },
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(aux["localInfo"]),
            "--result-contract",
            str(aux["resultContract"]),
            "--canary-report",
            str(aux["canary"]),
            "--hf-round-trip",
            str(aux["roundTripFull"]),
            "--hf-round-trip",
            str(aux["roundTripLite"]),
            "--quality-report",
            str(spoofedQuality),
            "--out",
            str(out),
            "--fail-on-release-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["opsReady"] is True
    assert report["releaseReady"] is False
    assert "qualityRealReviewedRows:0/100" in report["blockers"]
    assert "qualityMissingTarget:news" in report["blockers"]
    assert "qualityProxyGoldRows:120" in report["blockers"]
    assert "qualityUnreviewedGoldRows:120" in report["blockers"]


def test_productization_status_blocks_canary_missing_source_coverage(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    localInfo = _writeJson(
        tmp_path / "indexInfo.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(tmp_path / "resultContract.json", {"valid": True, "totalRows": 30, "invalidRows": []})
    canary = _writeJson(
        tmp_path / "canary.json",
        {
            "valid": True,
            "totalRows": 1,
            "passedRows": 1,
            "failures": [],
            "rows": [{"query": "공시 원문", "expectedSource": "allFilings", "passed": True}],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    quality = _writeJson(
        tmp_path / "quality.json",
        {
            "releaseEligible": True,
            "totalRows": 120,
            "realReviewedRows": 120,
            "coverageByKind": {"filing": 50, "news": 30, "noAnswer": 20, "edgar": 20},
            "goldOriginCounts": {"userLog": 120},
            "reviewStatusCounts": {"reviewed": 120},
        },
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(localInfo),
            "--result-contract",
            str(resultContract),
            "--canary-report",
            str(canary),
            "--hf-round-trip",
            str(roundTripFull),
            "--hf-round-trip",
            str(roundTripLite),
            "--quality-report",
            str(quality),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "canaryMissingSource:news" in report["blockers"]
    assert "canaryMissingSource:panel" in report["blockers"]


def test_productization_status_requires_source_manifest_set_in_remote_content(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    manifestPath = remote / "dart" / "contentIndex" / "manifest.json"
    manifest = json.loads(manifestPath.read_text(encoding="utf-8"))
    manifest.pop("sourceManifestSetId", None)
    manifest.pop("sourceManifestSet", None)
    manifestPath.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    localInfo = _writeJson(
        tmp_path / "indexInfo.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(tmp_path / "resultContract.json", {"valid": True, "totalRows": 30, "invalidRows": []})
    canary = _writeJson(
        tmp_path / "canary.json",
        {
            "valid": True,
            "totalRows": 4,
            "passedRows": 4,
            "failures": [],
            "rows": [
                {"query": "공시 원문", "expectedSource": "allFilings", "passed": True},
                {"query": "공시 원문 분기보고서", "expectedSource": "panel", "passed": True},
                {"query": "edgar filing", "expectedSource": "edgar-panel", "passed": True},
                {"query": "뉴스 기사", "expectedSource": "news", "passed": True},
            ],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(localInfo),
            "--result-contract",
            str(resultContract),
            "--canary-report",
            str(canary),
            "--hf-round-trip",
            str(roundTripFull),
            "--hf-round-trip",
            str(roundTripLite),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "remoteContentMissingSourceManifestSet:full" in report["blockers"]


def test_productization_status_requires_source_catalog_producer_run(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    manifestPath = remote / "dart" / "searchCatalog" / "allFilings" / "allFilings.source_manifest.json"
    manifest = json.loads(manifestPath.read_text(encoding="utf-8"))
    manifest.pop("producerRun", None)
    manifestPath.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    localInfo = _writeJson(
        tmp_path / "indexInfo.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(tmp_path / "resultContract.json", {"valid": True, "totalRows": 30, "invalidRows": []})
    canary = _writeJson(
        tmp_path / "canary.json",
        {
            "valid": True,
            "totalRows": 4,
            "passedRows": 4,
            "failures": [],
            "rows": [
                {"query": "공시 원문", "expectedSource": "allFilings", "passed": True},
                {"query": "공시 원문 분기보고서", "expectedSource": "panel", "passed": True},
                {"query": "edgar filing", "expectedSource": "edgar-panel", "passed": True},
                {"query": "뉴스 기사", "expectedSource": "news", "passed": True},
            ],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(localInfo),
            "--result-contract",
            str(resultContract),
            "--canary-report",
            str(canary),
            "--hf-round-trip",
            str(roundTripFull),
            "--hf-round-trip",
            str(roundTripLite),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "sourceCatalogMissingProducerRun:allFilings" in report["blockers"]


def test_productization_status_requires_content_manifest_set_producer_run(tmp_path: Path) -> None:
    remote = tmp_path / "remote"
    _writeCompleteRemote(remote)
    manifestSetPath = remote / "dart" / "contentIndex" / "_staging" / "run" / "source_manifest_set.json"
    manifestSet = json.loads(manifestSetPath.read_text(encoding="utf-8"))
    manifestSet["sources"][0].pop("producerRun", None)
    manifestSetPath.write_text(json.dumps(manifestSet, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    localInfo = _writeJson(
        tmp_path / "indexInfo.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(tmp_path / "resultContract.json", {"valid": True, "totalRows": 30, "invalidRows": []})
    canary = _writeJson(
        tmp_path / "canary.json",
        {
            "valid": True,
            "totalRows": 4,
            "passedRows": 4,
            "failures": [],
            "rows": [
                {"query": "공시 원문", "expectedSource": "allFilings", "passed": True},
                {"query": "공시 원문 분기보고서", "expectedSource": "panel", "passed": True},
                {"query": "edgar filing", "expectedSource": "edgar-panel", "passed": True},
                {"query": "뉴스 기사", "expectedSource": "news", "passed": True},
            ],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    out = tmp_path / "status.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-id",
            "fake/repo",
            "--remote-root",
            str(remote),
            "--local-index-info",
            str(localInfo),
            "--result-contract",
            str(resultContract),
            "--canary-report",
            str(canary),
            "--hf-round-trip",
            str(roundTripFull),
            "--hf-round-trip",
            str(roundTripLite),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert "remoteContentManifestSetMissingProducerRun:full:allFilings" in report["blockers"]


def _writeCompleteRemote(remote: Path) -> None:
    sourceManifestSet = {
        "schemaVersion": "searchSourceManifestSet.v1",
        "sourceManifestSetId": "manifest-set-1",
        "expectedSources": ["allFilings", "dartPanel", "edgarPanel", "newsPublic"],
        "combinedCatalogRows": 400,
        "sources": [
            {"source": source, "producerRun": _producerRun(source)}
            for source in ("allFilings", "dartPanel", "edgarPanel", "newsPublic")
        ],
    }
    for source in ("allFilings", "dartPanel", "edgarPanel", "newsPublic"):
        sourceDir = remote / "dart" / "searchCatalog" / source
        sourceDir.mkdir(parents=True, exist_ok=True)
        _writeJson(
            sourceDir / f"{source}.source_manifest.json",
            {
                "source": source,
                "snapshotScope": "full",
                "dataAsOf": "20260616",
                "builtAt": "2026-06-16T00:00:00Z",
                "totalRows": 100,
                "files": [{"path": f"{source}.parquet"}],
                "producer": "test",
                "producerRun": _producerRun(source),
            },
        )
        (sourceDir / f"{source}.catalog_snapshot.parquet").write_bytes(b"PAR1")
    _writeJson(
        remote / "dart" / "contentIndex" / "manifest.json",
        {
            "valid": True,
            "artifactVersion": "test",
            "schemaVersion": 2,
            "builtAt": "2026-06-16T00:00:00Z",
            "publishMode": "manifestPointer",
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
            "sourceManifestSetId": "manifest-set-1",
            "sourceManifestSet": {
                "sources": [
                    {"source": "allFilings"},
                    {"source": "dartPanel"},
                    {"source": "edgarPanel"},
                    {"source": "newsPublic"},
                ]
            },
            "requiredFiles": ["main.npz", "source_manifest_set.json"],
            "fileSources": {
                "main.npz": "_staging/run/main.npz",
                "source_manifest_set.json": "_staging/run/source_manifest_set.json",
            },
        },
    )
    (remote / "dart" / "contentIndex" / "_staging" / "run").mkdir(parents=True, exist_ok=True)
    (remote / "dart" / "contentIndex" / "_staging" / "run" / "main.npz").write_bytes(b"main")
    _writeJson(remote / "dart" / "contentIndex" / "_staging" / "run" / "source_manifest_set.json", sourceManifestSet)
    _writeJson(
        remote / "dart" / "contentIndex" / "lite" / "manifest.json",
        {
            "valid": True,
            "artifactVersion": "test-lite",
            "schemaVersion": 2,
            "builtAt": "2026-06-16T00:00:00Z",
            "publishMode": "manifestPointer",
            "nDocsBySource": {"allFilings": 20, "panel": 20, "edgar-panel": 20, "news": 20},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
            "sourceManifestSetId": "manifest-set-1",
            "sourceManifestSet": {
                "sources": [
                    {"source": "allFilings"},
                    {"source": "dartPanel"},
                    {"source": "edgarPanel"},
                    {"source": "newsPublic"},
                ]
            },
            "requiredFiles": ["main.npz", "source_manifest_set.json"],
            "fileSources": {
                "main.npz": "_staging/run-lite/main.npz",
                "source_manifest_set.json": "_staging/run-lite/source_manifest_set.json",
            },
        },
    )
    (remote / "dart" / "contentIndex" / "lite" / "_staging" / "run-lite").mkdir(parents=True, exist_ok=True)
    (remote / "dart" / "contentIndex" / "lite" / "_staging" / "run-lite" / "main.npz").write_bytes(b"lite")
    _writeJson(
        remote / "dart" / "contentIndex" / "lite" / "_staging" / "run-lite" / "source_manifest_set.json",
        sourceManifestSet,
    )


def _writeJson(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def _writeCompleteAuxEvidence(tmp_path: Path) -> dict[str, Path]:
    localInfo = _writeJson(
        tmp_path / "indexInfo.complete.json",
        {
            "available": True,
            "compatible": True,
            "manifestValid": True,
            "nDocs": 400,
            "nDocsBySource": {"allFilings": 100, "panel": 100, "edgar-panel": 100, "news": 100},
            "sourceDataAsOf": {
                "allFilings": "20260616",
                "panel": "20260616",
                "edgar-panel": "20260616",
                "news": "20260616",
            },
        },
    )
    resultContract = _writeJson(
        tmp_path / "resultContract.complete.json",
        {"valid": True, "totalRows": 30, "invalidRows": []},
    )
    canary = _writeJson(
        tmp_path / "canary.complete.json",
        {
            "valid": True,
            "totalRows": 4,
            "passedRows": 4,
            "failures": [],
            "rows": [
                {"query": "공시 원문", "expectedSource": "allFilings", "passed": True},
                {"query": "DART panel", "expectedSource": "panel", "passed": True},
                {"query": "EDGAR 10-K", "expectedSource": "edgar-panel", "passed": True},
                {"query": "뉴스", "expectedSource": "news", "passed": True},
            ],
        },
    )
    roundTripFull = _writeJson(
        tmp_path / "roundTrip.full.complete.json",
        {"valid": True, "tier": "full", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    roundTripLite = _writeJson(
        tmp_path / "roundTrip.lite.complete.json",
        {"valid": True, "tier": "lite", "activation": {"activated": True}, "rollback": {"rolledBack": True}},
    )
    return {
        "localInfo": localInfo,
        "resultContract": resultContract,
        "canary": canary,
        "roundTripFull": roundTripFull,
        "roundTripLite": roundTripLite,
    }


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
