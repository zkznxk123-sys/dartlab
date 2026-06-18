"""Build S4 default-replacement evidence for product search cutover.

This script does not mutate search artifacts. It reads the proof bundle,
remote evidence, round-trip reports, and workflow files, then emits the
replacement evidence consumed by ``evaluateSearchCutover.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-bundle", required=True)
    parser.add_argument("--remote-evidence", help="Remote evidence JSON path.")
    parser.add_argument("--round-trip", action="append", default=[], help="HF round-trip report JSON path.")
    parser.add_argument("--workflow", action="append", default=[], help="Workflow YAML files to inspect.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    evidence = buildReplacementEvidence(
        proofBundlePath=Path(args.proof_bundle),
        remoteEvidencePath=Path(args.remote_evidence) if args.remote_evidence else None,
        roundTripPaths=[Path(path) for path in args.round_trip],
        workflowPaths=[Path(path) for path in args.workflow],
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "valid": evidence["valid"],
                "blockers": evidence["blockers"],
                "activeManifestId": evidence.get("activeManifestId", ""),
                "previousManifestId": evidence.get("previousManifestId", ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.fail_on_incomplete and not evidence["valid"]:
        return 1
    return 0


def buildReplacementEvidence(
    *,
    proofBundlePath: Path,
    remoteEvidencePath: Path | None = None,
    roundTripPaths: list[Path] | None = None,
    workflowPaths: list[Path] | None = None,
) -> dict[str, Any]:
    proof = _loadJson(proofBundlePath)
    remote = _loadJson(remoteEvidencePath) if remoteEvidencePath and remoteEvidencePath.exists() else {}
    roundTrips = [_loadJson(path) for path in (roundTripPaths or []) if path.exists()]
    workflows = {str(path): _readText(path) for path in workflowPaths or []}

    activeManifestId = _activeManifestId(remote, roundTrips)
    previousManifestId = _previousManifestId(roundTrips)
    rollbackVerified = _rollbackVerified(roundTrips)
    runEvidenceRecorded = _runEvidenceRecorded(remote, proof)
    surfaceNamingReviewed = _surfaceNamingReviewed()
    singleEngineDefault = _singleEngineDefault(workflows)
    defaultBuildMode = "catalog" if _defaultBuildModeCatalog(workflows) else ""
    scheduledBuildMode = "catalog" if _scheduledBuildModeCatalog(workflows) else ""
    failClosedPublish = _failClosedPublish(workflows)
    legacyFallbackOperatorOnly = _legacyFallbackOperatorOnly(workflows)

    evidence: dict[str, Any] = {
        "proofBundle": str(proofBundlePath),
        "singleEngineDefault": singleEngineDefault,
        "defaultBuildMode": defaultBuildMode,
        "scheduledBuildMode": scheduledBuildMode,
        "legacyFallbackOperatorOnly": legacyFallbackOperatorOnly,
        "failClosedPublish": failClosedPublish,
        "activeManifestId": activeManifestId,
        "previousManifestId": previousManifestId,
        "rollbackCommand": "uv run python -X utf8 .github/scripts/search/verifySearchHfRoundTrip.py --tier full --fail-on-error",
        "rollbackVerified": rollbackVerified,
        "runEvidenceRecorded": runEvidenceRecorded,
        "surfaceNamingReviewed": surfaceNamingReviewed,
        "inputs": {
            "remoteEvidence": str(remoteEvidencePath or ""),
            "roundTrips": [str(path) for path in roundTripPaths or []],
            "workflows": [str(path) for path in workflowPaths or []],
        },
        "activeManifest": _activeManifestSummary(remote, roundTrips),
        "previousManifest": _previousManifestSummary(roundTrips),
    }
    blockers = _replacementBlockers(evidence)
    evidence["valid"] = not blockers
    evidence["blockers"] = blockers
    return evidence


def _activeManifestId(remote: dict[str, Any], roundTrips: list[dict[str, Any]]) -> str:
    manifest = _remoteFullManifest(remote) or _firstManifest(roundTrips, "activatedManifest")
    return _stableId("active", manifest)


def _previousManifestId(roundTrips: list[dict[str, Any]]) -> str:
    manifest = _firstManifest(roundTrips, "restoredManifest")
    return _stableId("previous", manifest)


def _activeManifestSummary(remote: dict[str, Any], roundTrips: list[dict[str, Any]]) -> dict[str, Any]:
    return _remoteFullManifest(remote) or _firstManifest(roundTrips, "activatedManifest")


def _previousManifestSummary(roundTrips: list[dict[str, Any]]) -> dict[str, Any]:
    return _firstManifest(roundTrips, "restoredManifest")


def _remoteFullManifest(remote: dict[str, Any]) -> dict[str, Any]:
    content = remote.get("contentIndex") if isinstance(remote.get("contentIndex"), dict) else {}
    manifests = content.get("manifests") if isinstance(content.get("manifests"), dict) else {}
    full = manifests.get("full") if isinstance(manifests.get("full"), dict) else {}
    manifest = full.get("manifest") if isinstance(full.get("manifest"), dict) else {}
    return dict(manifest)


def _firstManifest(roundTrips: list[dict[str, Any]], field: str) -> dict[str, Any]:
    for report in roundTrips:
        manifest = report.get(field) if isinstance(report.get(field), dict) else {}
        if manifest:
            return dict(manifest)
    return {}


def _rollbackVerified(roundTrips: list[dict[str, Any]]) -> bool:
    if not roundTrips:
        return False
    tiers = {str(report.get("tier") or "") for report in roundTrips}
    if not {"full", "lite"}.issubset(tiers):
        return False
    for report in roundTrips:
        rollback = report.get("rollback") if isinstance(report.get("rollback"), dict) else {}
        activation = report.get("activation") if isinstance(report.get("activation"), dict) else {}
        if not report.get("valid") or not activation.get("activated") or not rollback.get("rolledBack"):
            return False
    return True


def _runEvidenceRecorded(remote: dict[str, Any], proof: dict[str, Any]) -> bool:
    if proof.get("missingEvidence"):
        return False
    if not proof.get("opsReady") or not proof.get("releaseReady"):
        return False
    sourceCatalog = remote.get("sourceCatalog") if isinstance(remote.get("sourceCatalog"), dict) else {}
    sources = sourceCatalog.get("sources") if isinstance(sourceCatalog.get("sources"), dict) else {}
    if not sources:
        return False
    for item in sources.values():
        manifest = item.get("manifest") if isinstance(item, dict) and isinstance(item.get("manifest"), dict) else {}
        producerRun = manifest.get("producerRun") if isinstance(manifest.get("producerRun"), dict) else {}
        for field in ("workflow", "job", "runId", "sha", "artifactName"):
            if not str(producerRun.get(field) or "").strip():
                return False
    return True


def _surfaceNamingReviewed() -> bool:
    initPath = Path("src/dartlab/__init__.py")
    apiPath = Path("src/dartlab/providers/dart/search/api.py")
    initText = _readText(initPath)
    apiText = _readText(apiPath)
    return (
        "def search(" in initText
        and "from dartlab.providers.dart.search import search as _search" in initText
        and "def search(" in apiText
    )


def _singleEngineDefault(workflows: dict[str, str]) -> bool:
    # compact-only — 단일 searchIndexBuild 워크플로(MAIN_MODE catalog)에 별도 delta 엔진 없음.
    build = _workflowText(workflows, "searchIndexBuild.yml")
    return "DARTLAB_SEARCH_MAIN_MODE" in build and "DARTLAB_SEARCH_DELTA_MODE" not in build


def _defaultBuildModeCatalog(workflows: dict[str, str]) -> bool:
    build = _workflowText(workflows, "searchIndexBuild.yml")
    return "default: catalog" in build


def _scheduledBuildModeCatalog(workflows: dict[str, str]) -> bool:
    build = _workflowText(workflows, "searchIndexBuild.yml")
    return "${{ inputs.build_mode || 'catalog' }}" in build


def _legacyFallbackOperatorOnly(workflows: dict[str, str]) -> bool:
    build = _workflowText(workflows, "searchIndexBuild.yml")
    return "options:\n          - catalog\n          - legacy" in build


def _failClosedPublish(workflows: dict[str, str]) -> bool:
    combined = "\n".join(workflows.values())
    required = (
        'DARTLAB_SEARCH_PROMOTE_CURRENT: "0"',
        "--manifest-repo-path",
        "evaluateSearchResultContract.py",
        "evaluateSearchCanary.py",
        "promoteSearchCandidate.py",
        "buildSearchReplacementEvidence.py",
        "--replacement-evidence",
    )
    return all(item in combined for item in required)


def _workflowText(workflows: dict[str, str], suffix: str) -> str:
    for path, text in workflows.items():
        if path.replace("\\", "/").endswith(suffix):
            return text
    return ""


def _replacementBlockers(evidence: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in (
        "singleEngineDefault",
        "legacyFallbackOperatorOnly",
        "failClosedPublish",
        "runEvidenceRecorded",
        "rollbackVerified",
        "surfaceNamingReviewed",
    ):
        if not evidence.get(field):
            blockers.append(f"missing:{field}")
    if evidence.get("defaultBuildMode") != "catalog":
        blockers.append("invalid:defaultBuildMode")
    if evidence.get("scheduledBuildMode") != "catalog":
        blockers.append("invalid:scheduledBuildMode")
    for field in ("activeManifestId", "previousManifestId", "rollbackCommand"):
        if not str(evidence.get(field) or "").strip():
            blockers.append(f"missing:{field}")
    return blockers


def _stableId(prefix: str, payload: dict[str, Any]) -> str:
    if not payload:
        return ""
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]}"


def _loadJson(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _readText(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _splitCsv(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


if __name__ == "__main__":
    raise SystemExit(main())
