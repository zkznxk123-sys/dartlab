"""Evaluate search productization readiness from evidence reports.

This script is the operator-facing release guard: it does not build an index and
does not publish anything. It reads the same proof bundle that operators must
keep for search productization and returns explicit blockers for design-ready,
ops-ready, and release-ready.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_SOURCES = "allFilings,dartPanel,edgarPanel,newsPublic"
DEFAULT_TIERS = "full,lite"
DEFAULT_MIN_QUALITY_ROWS = 100
DEFAULT_REQUIRED_TARGETS = ("filing", "news", "noAnswer", "edgar")
REAL_GOLD_ORIGINS = {"real", "operator", "operatorReal", "userLog", "production"}
REVIEWED_STATUSES = {"reviewed", "approved", "accepted", "gold"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", help="HF dataset repository id. Defaults to DartLab contentIndex repo.")
    parser.add_argument("--remote-root", help="Local fake HF root for tests/offline drills.")
    parser.add_argument("--expected-sources", default=DEFAULT_SOURCES)
    parser.add_argument("--content-tiers", default=DEFAULT_TIERS)
    parser.add_argument("--remote-evidence", help="Existing searchRemoteEvidence JSON. If omitted, audit HF now.")
    parser.add_argument("--result-contract", help="searchResultContract JSON report.")
    parser.add_argument("--quality-report", help="query-log gold quality JSON report.")
    parser.add_argument("--canary-report", help="source/no-answer canary JSON report.")
    parser.add_argument(
        "--hf-round-trip",
        action="append",
        default=[],
        help="searchHfRoundTrip JSON report. Pass once per content tier.",
    )
    parser.add_argument("--local-index-info", help="Existing dartlab.search.indexInfo() JSON report.")
    parser.add_argument("--out", required=True, help="Output JSON report path.")
    parser.add_argument("--fail-on-ops-not-ready", action="store_true")
    parser.add_argument("--fail-on-release-not-ready", action="store_true")
    args = parser.parse_args(argv)

    report = evaluateProductizationStatus(
        repoId=args.repo_id or _defaultRepoId(),
        expectedSources=_splitCsv(args.expected_sources),
        contentTiers=_splitCsv(args.content_tiers),
        remoteRoot=Path(args.remote_root) if args.remote_root else None,
        remoteEvidencePath=Path(args.remote_evidence) if args.remote_evidence else None,
        resultContractPath=Path(args.result_contract) if args.result_contract else None,
        qualityReportPath=Path(args.quality_report) if args.quality_report else None,
        canaryReportPath=Path(args.canary_report) if args.canary_report else None,
        hfRoundTripPaths=[Path(path) for path in args.hf_round_trip],
        localIndexInfoPath=Path(args.local_index_info) if args.local_index_info else None,
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "designReady": report["designReady"],
                "opsReady": report["opsReady"],
                "releaseReady": report["releaseReady"],
                "blockers": report["blockers"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.fail_on_release_not_ready and not report["releaseReady"]:
        return 1
    if args.fail_on_ops_not_ready and not report["opsReady"]:
        return 1
    return 0


def evaluateProductizationStatus(
    *,
    repoId: str,
    expectedSources: list[str],
    contentTiers: list[str],
    remoteRoot: Path | None = None,
    remoteEvidencePath: Path | None = None,
    resultContractPath: Path | None = None,
    qualityReportPath: Path | None = None,
    canaryReportPath: Path | None = None,
    hfRoundTripPath: Path | None = None,
    hfRoundTripPaths: list[Path] | None = None,
    localIndexInfoPath: Path | None = None,
) -> dict[str, Any]:
    remoteEvidence = (
        _loadJsonReport(remoteEvidencePath)
        if remoteEvidencePath
        else _auditRemoteEvidence(
            repoId=repoId,
            expectedSources=expectedSources,
            contentTiers=contentTiers,
            remoteRoot=remoteRoot,
        )
    )
    resultContract = _loadJsonReport(resultContractPath)
    qualityReport = _loadJsonReport(qualityReportPath)
    canaryReport = _loadJsonReport(canaryReportPath)
    hfRoundTripReports = _loadRoundTripReports(hfRoundTripPaths or ([hfRoundTripPath] if hfRoundTripPath else []))
    localIndexInfo = _loadIndexInfo(localIndexInfoPath)

    blockers = _blockers(
        expectedSources=expectedSources,
        contentTiers=contentTiers,
        remoteEvidence=remoteEvidence,
        resultContract=resultContract,
        qualityReport=qualityReport,
        canaryReport=canaryReport,
        hfRoundTripReports=hfRoundTripReports,
        localIndexInfo=localIndexInfo,
    )
    stageBlockers = _stageBlockers(blockers)
    opsReady = not stageBlockers["ops"]
    releaseReady = opsReady and not stageBlockers["release"]
    return {
        "designReady": True,
        "opsReady": opsReady,
        "releaseReady": releaseReady,
        "blockers": blockers,
        "stageBlockers": stageBlockers,
        "evidence": {
            "remoteEvidence": _remoteSummary(remoteEvidence),
            "resultContract": _resultContractSummary(resultContract),
            "qualityReport": _qualitySummary(qualityReport),
            "canaryReport": _canarySummary(canaryReport),
            "hfRoundTrip": _roundTripSummary(hfRoundTripReports, contentTiers),
            "localIndexInfo": _localIndexSummary(localIndexInfo),
        },
    }


def _blockers(
    *,
    expectedSources: list[str],
    contentTiers: list[str],
    remoteEvidence: dict[str, Any],
    resultContract: dict[str, Any],
    qualityReport: dict[str, Any],
    canaryReport: dict[str, Any],
    hfRoundTripReports: list[dict[str, Any]],
    localIndexInfo: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not remoteEvidence:
        blockers.append("missingRemoteEvidence")
    elif not _isTruthy(remoteEvidence.get("valid")):
        blockers.extend(_remoteBlockers(remoteEvidence))
    else:
        blockers.extend(_remoteSourceCatalogBlockers(remoteEvidence, expectedSources))
        blockers.extend(_remoteContentIndexBlockers(remoteEvidence, expectedSources))
    if not localIndexInfo:
        blockers.append("missingLocalIndexInfo")
    else:
        if not _isTruthy(localIndexInfo.get("available")):
            blockers.append("localIndexUnavailable")
        if not _isTruthy(localIndexInfo.get("compatible")):
            blockers.append("localIndexIncompatible")
        if not _isTruthy(localIndexInfo.get("manifestValid"), default=True):
            blockers.append("localIndexManifestInvalid")
        if _isEmptyMapping(localIndexInfo.get("nDocsBySource")):
            blockers.append("localIndexMissingSourceCounts")
        else:
            blockers.extend(_localSourceCountBlockers(localIndexInfo, expectedSources))
        blockers.extend(_localSourceFreshnessBlockers(localIndexInfo, expectedSources))
    if not hfRoundTripReports:
        blockers.append("missingHfRoundTripReport")
    else:
        blockers.extend(_roundTripBlockers(hfRoundTripReports, contentTiers))
    if not resultContract:
        blockers.append("missingResultContractReport")
    elif not _isValidReport(resultContract):
        blockers.append("resultContractInvalid")
    if not canaryReport:
        blockers.append("missingCanaryReport")
    elif not _isValidReport(canaryReport):
        blockers.append("canaryInvalid")
    else:
        blockers.extend(_canaryCoverageBlockers(canaryReport, expectedSources))
    if not qualityReport:
        blockers.append("missingQualityReport")
    else:
        blockers.extend(_qualityBlockers(qualityReport))
    return _dedupe(blockers)


def _qualityBlockers(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not _isTruthy(report.get("releaseEligible")):
        blockers.append("qualityNotReleaseEligible")
    totalRows = _int(report.get("totalRows"), 0)
    realReviewedRows = _int(report.get("realReviewedRows"), 0)
    if totalRows < DEFAULT_MIN_QUALITY_ROWS:
        blockers.append(f"qualityMinRows:{totalRows}/{DEFAULT_MIN_QUALITY_ROWS}")
    if realReviewedRows < DEFAULT_MIN_QUALITY_ROWS:
        blockers.append(f"qualityRealReviewedRows:{realReviewedRows}/{DEFAULT_MIN_QUALITY_ROWS}")
    coverage = report.get("coverageByKind") if isinstance(report.get("coverageByKind"), dict) else {}
    for target in DEFAULT_REQUIRED_TARGETS:
        if _int(coverage.get(target), 0) <= 0:
            blockers.append(f"qualityMissingTarget:{target}")
    originCounts = report.get("goldOriginCounts") if isinstance(report.get("goldOriginCounts"), dict) else {}
    reviewCounts = report.get("reviewStatusCounts") if isinstance(report.get("reviewStatusCounts"), dict) else {}
    if originCounts:
        proxyRows = sum(
            _int(count, 0) for origin, count in originCounts.items() if str(origin) not in REAL_GOLD_ORIGINS
        )
        if proxyRows:
            blockers.append(f"qualityProxyGoldRows:{proxyRows}")
    else:
        blockers.append("qualityMissingGoldOriginCounts")
    if reviewCounts:
        unreviewedRows = sum(
            _int(count, 0) for status, count in reviewCounts.items() if str(status) not in REVIEWED_STATUSES
        )
        if unreviewedRows:
            blockers.append(f"qualityUnreviewedGoldRows:{unreviewedRows}")
    else:
        blockers.append("qualityMissingReviewStatusCounts")
    for blocker in report.get("blockers") or []:
        if blocker:
            blockers.append(f"qualityReportBlocker:{blocker}")
    return blockers


def _stageBlockers(blockers: list[str]) -> dict[str, list[str]]:
    opsPrefixes = (
        "missingRemoteEvidence",
        "sourceCatalogMissing",
        "sourceCatalog",
        "remoteContent",
        "contentIndexManifestMissing",
        "missingLocalIndexInfo",
        "localIndex",
        "missingHfRoundTripReport",
        "hfRoundTrip",
        "missingResultContractReport",
        "resultContract",
        "missingCanaryReport",
        "canary",
    )
    releasePrefixes = ("missingQualityReport", "quality")
    return {
        "ops": [blocker for blocker in blockers if blocker.startswith(opsPrefixes)],
        "release": [blocker for blocker in blockers if blocker.startswith(releasePrefixes)],
    }


def _auditRemoteEvidence(
    *,
    repoId: str,
    expectedSources: list[str],
    contentTiers: list[str],
    remoteRoot: Path | None,
) -> dict[str, Any]:
    from importlib import util

    path = Path(__file__).with_name("checkSearchRemoteEvidence.py")
    spec = util.spec_from_file_location("_dartlab_check_search_remote_evidence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.auditRemoteEvidence(
        repoId=repoId,
        expectedSources=expectedSources,
        contentTiers=contentTiers,
        remoteRoot=remoteRoot,
    )


def _loadIndexInfo(path: Path | None) -> dict[str, Any]:
    if path is not None:
        return _loadJsonReport(path)
    try:
        import dartlab

        info = dartlab.search.indexInfo()
        return dict(info) if isinstance(info, dict) else {}
    except Exception as exc:
        return {"available": False, "compatible": False, "loadError": f"{type(exc).__name__}:{exc}"}


def _loadJsonReport(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.exists():
        return {"exists": False, "loadError": "missingFile"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"valid": False, "loadError": "notObject"}
    except Exception as exc:
        return {"valid": False, "loadError": f"{type(exc).__name__}:{exc}"}


def _loadRoundTripReports(paths: list[Path | None]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in paths:
        if path is None:
            continue
        reports.append(_loadJsonReport(path))
    return reports


def _remoteBlockers(report: dict[str, Any]) -> list[str]:
    blockers = report.get("blockers")
    if isinstance(blockers, list) and blockers:
        return [str(item) for item in blockers if item]
    errors = report.get("errors")
    if isinstance(errors, list) and errors:
        out: list[str] = []
        if any(str(error).startswith("missingSource") for error in errors):
            out.append("sourceCatalogMissing")
        if any(str(error).startswith("missingContent") for error in errors):
            out.append("contentIndexManifestMissing")
        if any(str(error).startswith("missingContentFileSource") for error in errors):
            out.append("contentIndexFileSourceMissing")
        return out or [str(error) for error in errors if error]
    return ["remoteEvidenceInvalid"]


def _remoteSummary(report: dict[str, Any]) -> dict[str, Any]:
    sourceCatalog = report.get("sourceCatalog") if isinstance(report.get("sourceCatalog"), dict) else {}
    contentIndex = report.get("contentIndex") if isinstance(report.get("contentIndex"), dict) else {}
    manifests = contentIndex.get("manifests") if isinstance(contentIndex.get("manifests"), dict) else {}
    return {
        "valid": report.get("valid"),
        "blockers": report.get("blockers") or [],
        "repoId": report.get("repoId") or "",
        "fileCount": report.get("fileCount"),
        "missingSources": sourceCatalog.get("missingSources") or [],
        "contentErrors": contentIndex.get("errors") or [],
        "entityGraphCatalog": {
            tier: (item.get("manifest") or {}).get("entityGraphCatalog") or {}
            for tier, item in manifests.items()
            if isinstance(item, dict)
        },
    }


def _remoteSourceCatalogBlockers(report: dict[str, Any], expectedSources: list[str]) -> list[str]:
    sourceCatalog = report.get("sourceCatalog") if isinstance(report.get("sourceCatalog"), dict) else {}
    sources = sourceCatalog.get("sources") if isinstance(sourceCatalog.get("sources"), dict) else {}
    out: list[str] = []
    for source in expectedSources:
        item = sources.get(source) if isinstance(sources.get(source), dict) else {}
        manifest = item.get("manifest") if isinstance(item.get("manifest"), dict) else {}
        if not manifest:
            out.append(f"sourceCatalogManifestMissing:{source}")
            continue
        if str(manifest.get("snapshotScope") or "") != "full":
            out.append(f"sourceCatalogNotFull:{source}")
        if not str(manifest.get("dataAsOf") or "").strip():
            out.append(f"sourceCatalogMissingDataAsOf:{source}")
        if _int(manifest.get("totalRows"), 0) <= 0:
            out.append(f"sourceCatalogEmptyRows:{source}")
        if _int(manifest.get("fileCount"), 0) <= 0:
            out.append(f"sourceCatalogEmptyFiles:{source}")
        out.extend(_sourceProducerRunBlockers(source, manifest))
    return out


def _sourceProducerRunBlockers(source: str, manifest: dict[str, Any]) -> list[str]:
    producerRun = manifest.get("producerRun") if isinstance(manifest.get("producerRun"), dict) else {}
    if not producerRun:
        return [f"sourceCatalogMissingProducerRun:{source}"]
    required = ("workflow", "job", "runId", "sha", "artifactName")
    return [
        f"sourceCatalogMissingProducerRunField:{source}:{field}"
        for field in required
        if not str(producerRun.get(field) or "").strip()
    ]


def _remoteContentIndexBlockers(report: dict[str, Any], expectedSources: list[str]) -> list[str]:
    contentIndex = report.get("contentIndex") if isinstance(report.get("contentIndex"), dict) else {}
    manifests = contentIndex.get("manifests") if isinstance(contentIndex.get("manifests"), dict) else {}
    out: list[str] = []
    expected = sorted({_canonicalSource(source) for source in expectedSources if _canonicalSource(source)})
    for tier, item in manifests.items():
        if not isinstance(item, dict):
            continue
        manifest = item.get("manifest") if isinstance(item.get("manifest"), dict) else {}
        counts = manifest.get("nDocsBySource") if isinstance(manifest.get("nDocsBySource"), dict) else {}
        freshness = manifest.get("sourceDataAsOf") if isinstance(manifest.get("sourceDataAsOf"), dict) else {}
        for source in expected:
            if _int(counts.get(source), 0) <= 0:
                out.append(f"remoteContentMissingSourceCount:{tier}:{source}")
            if not str(freshness.get(source) or "").strip():
                out.append(f"remoteContentMissingSourceDataAsOf:{tier}:{source}")
        if _int(manifest.get("fileSourcesCount"), 0) <= 0:
            out.append(f"remoteContentMissingFileSources:{tier}")
        if not str(manifest.get("sourceManifestSetId") or "").strip():
            out.append(f"remoteContentMissingSourceManifestSet:{tier}")
        else:
            manifestSetSources = {
                str(source) for source in manifest.get("sourceManifestSetSources") or [] if str(source)
            }
            for source in expectedSources:
                if source not in manifestSetSources:
                    out.append(f"remoteContentManifestSetMissingSource:{tier}:{source}")
        for rel in manifest.get("missingFileSourceMappings") or []:
            out.append(f"remoteContentMissingFileSourceMapping:{tier}:{rel}")
        for rel in manifest.get("missingFileSources") or []:
            out.append(f"remoteContentMissingFileSource:{tier}:{rel}")
        for source in manifest.get("sourceManifestSetProducerRunMissingSources") or []:
            out.append(f"remoteContentManifestSetMissingProducerRun:{tier}:{source}")
    return out


def _resultContractSummary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": report.get("valid"),
        "totalRows": report.get("totalRows"),
        "blockers": report.get("blockers") or [],
        "invalidRows": len(report.get("invalidRows") or []) if isinstance(report.get("invalidRows"), list) else None,
    }


def _qualitySummary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "releaseEligible": report.get("releaseEligible"),
        "totalRows": report.get("totalRows"),
        "realReviewedRows": report.get("realReviewedRows"),
        "coverageByKind": report.get("coverageByKind") or {},
        "metrics": report.get("metrics") or {},
        "blockers": report.get("blockers") or [],
    }


def _canarySummary(report: dict[str, Any]) -> dict[str, Any]:
    expectedSources = _canaryPassedSources(report)
    return {
        "valid": report.get("valid"),
        "totalRows": report.get("totalRows"),
        "passedRows": report.get("passedRows"),
        "passedSources": sorted(expectedSources),
        "metrics": report.get("metrics") or {},
        "failures": len(report.get("failures") or []) if isinstance(report.get("failures"), list) else None,
    }


def _roundTripSummary(reports: list[dict[str, Any]], contentTiers: list[str]) -> dict[str, Any]:
    normalized = [_normalizeRoundTrip(report) for report in reports if report]
    missingTiers = _missingRoundTripTiers(normalized, contentTiers)
    return {
        "valid": bool(normalized) and not _roundTripBlockers(reports, contentTiers),
        "tiers": [item["tier"] for item in normalized if item.get("tier")],
        "missingTiers": missingTiers,
        "reports": normalized,
    }


def _roundTripBlockers(reports: list[dict[str, Any]], contentTiers: list[str]) -> list[str]:
    normalized = [_normalizeRoundTrip(report) for report in reports if report]
    blockers: list[str] = []
    for item in normalized:
        tier = item.get("tier") or "unknown"
        if not _isTruthy(item.get("valid")):
            blockers.append(f"hfRoundTripInvalid:{tier}")
        if not _isTruthy(item.get("activated")):
            blockers.append(f"hfRoundTripActivationFailed:{tier}")
        if not _isTruthy(item.get("rolledBack")):
            blockers.append(f"hfRoundTripRollbackFailed:{tier}")
    blockers.extend(f"hfRoundTripMissingTier:{tier}" for tier in _missingRoundTripTiers(normalized, contentTiers))
    return _dedupe(blockers)


def _normalizeRoundTrip(report: dict[str, Any]) -> dict[str, Any]:
    activation = report.get("activation") if isinstance(report.get("activation"), dict) else {}
    rollback = report.get("rollback") if isinstance(report.get("rollback"), dict) else {}
    return {
        "tier": report.get("tier") or "",
        "valid": report.get("valid"),
        "activated": report.get("activated") if "activated" in report else activation.get("activated"),
        "rolledBack": (
            report.get("rolledBack")
            if "rolledBack" in report
            else report.get("rollbackOk")
            if "rollbackOk" in report
            else rollback.get("rolledBack")
        ),
        "errors": report.get("blockers") or report.get("errors") or [],
        "activatedManifest": report.get("activatedManifest") or {},
    }


def _missingRoundTripTiers(normalized: list[dict[str, Any]], contentTiers: list[str]) -> list[str]:
    seen = {str(item.get("tier") or "") for item in normalized if item.get("tier")}
    return [tier for tier in contentTiers if tier not in seen]


def _localIndexSummary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": report.get("available"),
        "compatible": report.get("compatible"),
        "manifestValid": report.get("manifestValid"),
        "nDocs": report.get("nDocs"),
        "nDocsBySource": report.get("nDocsBySource") or {},
        "sourceDataAsOf": report.get("sourceDataAsOf") or {},
        "hasDelta": report.get("hasDelta"),
    }


def _isValidReport(report: dict[str, Any]) -> bool:
    if not report:
        return False
    if "valid" in report:
        return _isTruthy(report.get("valid"))
    if "success" in report:
        return _isTruthy(report.get("success"))
    return False


def _isTruthy(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "pass", "passed", "ok"}
    return bool(value)


def _isEmptyMapping(value: Any) -> bool:
    return not isinstance(value, dict) or not value


def _canaryCoverageBlockers(report: dict[str, Any], expectedSources: list[str]) -> list[str]:
    passedSources = _canaryPassedSources(report)
    expected = {_canonicalSource(source) for source in expectedSources if _canonicalSource(source)}
    missing = sorted(source for source in expected if source not in passedSources)
    return [f"canaryMissingSource:{source}" for source in missing]


def _localSourceCountBlockers(report: dict[str, Any], expectedSources: list[str]) -> list[str]:
    counts = report.get("nDocsBySource") if isinstance(report.get("nDocsBySource"), dict) else {}
    out: list[str] = []
    for source in sorted({_canonicalSource(source) for source in expectedSources if _canonicalSource(source)}):
        try:
            count = int(counts.get(source) or 0)
        except (TypeError, ValueError):
            count = 0
        if count <= 0:
            out.append(f"localIndexMissingSourceCount:{source}")
    return out


def _localSourceFreshnessBlockers(report: dict[str, Any], expectedSources: list[str]) -> list[str]:
    freshness = report.get("sourceDataAsOf") if isinstance(report.get("sourceDataAsOf"), dict) else {}
    out: list[str] = []
    for source in sorted({_canonicalSource(source) for source in expectedSources if _canonicalSource(source)}):
        if not str(freshness.get(source) or "").strip():
            out.append(f"localIndexMissingSourceDataAsOf:{source}")
    return out


def _canaryPassedSources(report: dict[str, Any]) -> set[str]:
    rows = report.get("rows")
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not _isTruthy(row.get("passed")):
            continue
        source = _canonicalSource(str(row.get("expectedSource") or ""))
        if source:
            out.add(source)
    return out


def _canonicalSource(source: str) -> str:
    return {
        "dartPanel": "panel",
        "edgarPanel": "edgar-panel",
        "newsPublic": "news",
    }.get(source, source)


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _splitCsv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _defaultRepoId() -> str:
    from dartlab.core.dataConfig import repoFor

    return repoFor("contentIndex")


if __name__ == "__main__":
    raise SystemExit(main())
