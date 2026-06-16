"""Search cutover state CLI tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SCRIPT = Path(".github/scripts/search/evaluateSearchCutover.py")


def test_cutover_report_keeps_ops_blockers_and_next_actions(tmp_path: Path) -> None:
    status = _writeJson(
        tmp_path / "status.json",
        {
            "designReady": True,
            "opsReady": False,
            "releaseReady": False,
            "blockers": ["sourceCatalogMissing", "contentIndexManifestMissing"],
        },
    )
    proof = _writeJson(
        tmp_path / "searchProofBundle.json",
        {
            "opsReady": False,
            "releaseReady": False,
            "missingEvidence": ["hfRoundTrip"],
            "blockers": ["sourceCatalogMissing", "contentIndexManifestMissing"],
            "reports": {"productizationStatus": str(status)},
            "nextActions": {"bootstrapPlan": {"path": "searchBootstrapPlan.json"}},
        },
    )
    out = tmp_path / "cutover.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--proof-bundle",
            str(proof),
            "--out",
            str(out),
            "--fail-on-ops-not-ready",
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
    assert report["state"] == "S1_DESIGN_READY"
    assert report["opsReady"] is False
    assert report["defaultReplacement"] is False
    assert "sourceCatalogMissing" in report["blockers"]
    assert "missingOpsEvidence:hfRoundTrip" in report["blockers"]
    assert report["nextActions"]["bootstrapPlan"]["path"] == "searchBootstrapPlan.json"


def test_cutover_report_treats_quality_as_release_only_evidence(tmp_path: Path) -> None:
    status = _writeJson(
        tmp_path / "status.json",
        {"designReady": True, "opsReady": True, "releaseReady": False, "blockers": ["missingQualityReport"]},
    )
    proof = _writeJson(
        tmp_path / "searchProofBundle.json",
        {
            "opsReady": True,
            "releaseReady": False,
            "missingEvidence": ["quality"],
            "blockers": ["missingQualityReport"],
            "reports": {"productizationStatus": str(status)},
        },
    )
    out = tmp_path / "cutover.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--proof-bundle",
            str(proof),
            "--out",
            str(out),
            "--fail-on-release-not-ready",
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
    assert report["state"] == "S2_OPS_READY"
    assert report["opsReady"] is True
    assert report["releaseReady"] is False
    assert report["missingOpsEvidence"] == []
    assert report["missingReleaseEvidence"] == ["quality"]
    assert "missingReleaseEvidence:quality" in report["blockers"]


def test_cutover_report_requires_replacement_evidence_for_default(tmp_path: Path) -> None:
    status = _writeJson(
        tmp_path / "status.json",
        {"designReady": True, "opsReady": True, "releaseReady": True, "blockers": []},
    )
    proof = _writeJson(
        tmp_path / "searchProofBundle.json",
        {
            "opsReady": True,
            "releaseReady": True,
            "missingEvidence": [],
            "blockers": [],
            "reports": {"productizationStatus": str(status)},
        },
    )
    out = tmp_path / "cutover.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--proof-bundle",
            str(proof),
            "--out",
            str(out),
            "--fail-on-default-not-ready",
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
    assert report["state"] == "S3_RELEASE_READY"
    assert report["releaseReady"] is True
    assert report["defaultReplacement"] is False
    assert "missingReplacementEvidence" in report["blockers"]


def test_cutover_report_accepts_default_replacement_evidence(tmp_path: Path) -> None:
    status = _writeJson(
        tmp_path / "status.json",
        {"designReady": True, "opsReady": True, "releaseReady": True, "blockers": []},
    )
    proof = _writeJson(
        tmp_path / "searchProofBundle.json",
        {
            "opsReady": True,
            "releaseReady": True,
            "missingEvidence": [],
            "blockers": [],
            "reports": {"productizationStatus": str(status)},
        },
    )
    replacement = _writeJson(
        tmp_path / "replacement.json",
        {
            "proofBundle": str(proof),
            "singleEngineDefault": True,
            "defaultBuildMode": "catalog",
            "scheduledBuildMode": "catalog",
            "legacyFallbackOperatorOnly": True,
            "failClosedPublish": True,
            "activeManifestId": "manifest-current",
            "previousManifestId": "manifest-previous",
            "rollbackCommand": 'uv run python -X utf8 -c "rollback"',
            "rollbackVerified": True,
            "runEvidenceRecorded": True,
            "surfaceNamingReviewed": True,
        },
    )
    out = tmp_path / "cutover.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--proof-bundle",
            str(proof),
            "--replacement-evidence",
            str(replacement),
            "--out",
            str(out),
            "--fail-on-default-not-ready",
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
    assert report["state"] == "S4_DEFAULT_REPLACEMENT"
    assert report["defaultReplacement"] is True
    assert report["blockers"] == []


def test_cutover_report_rejects_ambiguous_default_replacement_evidence(tmp_path: Path) -> None:
    status = _writeJson(
        tmp_path / "status.json",
        {"designReady": True, "opsReady": True, "releaseReady": True, "blockers": []},
    )
    proof = _writeJson(
        tmp_path / "searchProofBundle.json",
        {
            "opsReady": True,
            "releaseReady": True,
            "missingEvidence": [],
            "blockers": [],
            "reports": {"productizationStatus": str(status)},
        },
    )
    replacement = _writeJson(
        tmp_path / "replacement.json",
        {
            "proofBundle": str(proof),
            "singleEngineDefault": True,
            "defaultBuildMode": "auto",
            "scheduledBuildMode": "auto",
            "activeManifestId": "manifest-current",
            "previousManifestId": "manifest-previous",
            "rollbackCommand": 'uv run python -X utf8 -c "rollback"',
            "rollbackVerified": True,
            "runEvidenceRecorded": True,
            "surfaceNamingReviewed": True,
        },
    )
    out = tmp_path / "cutover.json"

    proc = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--proof-bundle",
            str(proof),
            "--replacement-evidence",
            str(replacement),
            "--out",
            str(out),
            "--fail-on-default-not-ready",
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
    assert report["state"] == "S3_RELEASE_READY"
    assert "replacementEvidenceInvalid:defaultBuildMode" in report["blockers"]
    assert "replacementEvidenceInvalid:scheduledBuildMode" in report["blockers"]
    assert "replacementEvidenceMissing:legacyFallbackOperatorOnly" in report["blockers"]
    assert "replacementEvidenceMissing:failClosedPublish" in report["blockers"]


def _writeJson(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path
