"""Run the reviewed search quality cycle end to end.

The cycle intentionally starts from explicit reviewer decisions. Undecided
review-pack labels fail before any canonical gold or quality report is treated
as release evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True, help="raw query-log JSONL path")
    parser.add_argument("--labels", help="todo labels with explicit reviewDecision rows")
    parser.add_argument("--reviewed-labels", help="already finalized reviewed labels JSONL")
    parser.add_argument("--out-dir", required=True, help="cycle output directory")
    parser.add_argument("--reviewer", default="", help="fallback reviewer id for finalize step")
    parser.add_argument("--reviewed-at", default="", help="fallback reviewedAt value for finalize step")
    parser.add_argument("--batch-accept-suggested", action="store_true", help="apply suggested review decisions first")
    parser.add_argument("--batch-quality-ceiling", help="optional proposal quality ceiling report for batch approval")
    parser.add_argument("--batch-require-metric-eligible", action="store_true")
    parser.add_argument("--batch-evidence-packet", help="optional review evidence packet for batch approval")
    parser.add_argument("--batch-require-evidence-ready", action="store_true")
    parser.add_argument("--results-json", help="precomputed search results for evaluateSearchGold.py")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--required-targets", default="filing,news,noAnswer,edgar")
    parser.add_argument("--remote-evidence", help="optional productization status remote evidence JSON")
    parser.add_argument("--result-contract", help="optional productization status result contract JSON")
    parser.add_argument("--canary-report", help="optional productization status canary JSON")
    parser.add_argument("--hf-round-trip", action="append", default=[], help="optional round-trip report JSON")
    parser.add_argument("--local-index-info", help="optional local index info JSON")
    parser.add_argument("--fail-on-release-not-ready", action="store_true")
    args = parser.parse_args(argv)

    if not args.labels and not args.reviewed_labels:
        raise SystemExit("--labels or --reviewed-labels is required")

    report = runQualityCycle(
        rawPath=Path(args.raw),
        labelsPath=Path(args.labels) if args.labels else None,
        reviewedLabelsPath=Path(args.reviewed_labels) if args.reviewed_labels else None,
        outDir=Path(args.out_dir),
        reviewer=args.reviewer,
        reviewedAt=args.reviewed_at,
        resultsJson=Path(args.results_json) if args.results_json else None,
        limit=args.limit,
        scope=args.scope,
        minRows=args.min_rows,
        requiredTargets=args.required_targets,
        remoteEvidence=Path(args.remote_evidence) if args.remote_evidence else None,
        resultContract=Path(args.result_contract) if args.result_contract else None,
        canaryReport=Path(args.canary_report) if args.canary_report else None,
        hfRoundTrips=[Path(path) for path in args.hf_round_trip],
        localIndexInfo=Path(args.local_index_info) if args.local_index_info else None,
        failOnReleaseNotReady=args.fail_on_release_not_ready,
        batchAcceptSuggested=args.batch_accept_suggested,
        batchQualityCeiling=Path(args.batch_quality_ceiling) if args.batch_quality_ceiling else None,
        batchRequireMetricEligible=args.batch_require_metric_eligible,
        batchEvidencePacket=Path(args.batch_evidence_packet) if args.batch_evidence_packet else None,
        batchRequireEvidenceReady=args.batch_require_evidence_ready,
    )
    print(json.dumps({"valid": report["valid"], "failedPhase": report["failedPhase"]}, ensure_ascii=False))
    return 0 if report["valid"] else 1


def runQualityCycle(
    *,
    rawPath: Path,
    labelsPath: Path | None,
    reviewedLabelsPath: Path | None,
    outDir: Path,
    reviewer: str,
    reviewedAt: str,
    resultsJson: Path | None,
    limit: int,
    scope: str,
    minRows: int,
    requiredTargets: str,
    remoteEvidence: Path | None,
    resultContract: Path | None,
    canaryReport: Path | None,
    hfRoundTrips: Sequence[Path],
    localIndexInfo: Path | None,
    failOnReleaseNotReady: bool,
    batchAcceptSuggested: bool = False,
    batchQualityCeiling: Path | None = None,
    batchRequireMetricEligible: bool = False,
    batchEvidencePacket: Path | None = None,
    batchRequireEvidenceReady: bool = False,
) -> dict[str, Any]:
    outDir.mkdir(parents=True, exist_ok=True)
    cyclePath = outDir / "searchQualityCycle.json"
    reviewedLabels = reviewedLabelsPath or (outDir / "queryLogLabels.reviewed.jsonl")
    finalizeSummary = outDir / "queryLogLabels.reviewed.summary.json"
    goldPath = outDir / "queryLogGold.real.jsonl"
    goldSummary = outDir / "queryLogGold.summary.json"
    qualityReport = outDir / "qualityReport.json"
    missLedger = outDir / "missLedger.jsonl"
    statusReport = outDir / "searchProductizationStatus.json"
    batchReviewedSheet = outDir / "queryLogDecisionSheet.batchReviewed.jsonl"
    batchSummary = outDir / "queryLogDecisionSheet.batchReviewed.summary.json"

    phases: list[dict[str, Any]] = []
    if reviewedLabelsPath is None:
        assert labelsPath is not None
        if batchAcceptSuggested:
            batchCmd = [
                sys.executable,
                "-X",
                "utf8",
                str(_scriptPath("applySearchReviewBatchDecision.py")),
                "--sheet",
                str(labelsPath),
                "--out",
                str(batchReviewedSheet),
                "--summary",
                str(batchSummary),
                "--reviewer",
                reviewer,
                "--accept-suggested",
            ]
            if reviewedAt:
                batchCmd.extend(["--reviewed-at", reviewedAt])
            if batchQualityCeiling:
                batchCmd.extend(["--quality-ceiling", str(batchQualityCeiling)])
            if batchRequireMetricEligible:
                batchCmd.append("--require-metric-eligible")
            if batchEvidencePacket:
                batchCmd.extend(["--evidence-packet", str(batchEvidencePacket)])
            if batchRequireEvidenceReady:
                batchCmd.append("--require-evidence-ready")
            phase = _runPhase("batchReviewDecisions", batchCmd)
            phases.append(phase)
            if phase["returncode"] != 0:
                return _writeCycleReport(
                    cyclePath,
                    phases=phases,
                    failedPhase="batchReviewDecisions",
                    paths=_paths(
                        reviewedLabels,
                        finalizeSummary,
                        goldPath,
                        goldSummary,
                        qualityReport,
                        missLedger,
                        statusReport,
                        batchReviewedSheet,
                        batchSummary,
                    ),
                )
            labelsPath = batchReviewedSheet
        finalizeCmd = [
            sys.executable,
            "-X",
            "utf8",
            str(_scriptPath("finalizeSearchReviewLabels.py")),
            "--labels",
            str(labelsPath),
            "--out",
            str(reviewedLabels),
            "--summary",
            str(finalizeSummary),
        ]
        if reviewer:
            finalizeCmd.extend(["--reviewer", reviewer])
        if reviewedAt:
            finalizeCmd.extend(["--reviewed-at", reviewedAt])
        phase = _runPhase("finalizeLabels", finalizeCmd)
        phases.append(phase)
        if phase["returncode"] != 0:
            return _writeCycleReport(
                cyclePath,
                phases=phases,
                failedPhase="finalizeLabels",
                paths=_paths(
                    reviewedLabels,
                    finalizeSummary,
                    goldPath,
                    goldSummary,
                    qualityReport,
                    missLedger,
                    statusReport,
                ),
            )

    prepareCmd = [
        sys.executable,
        "-X",
        "utf8",
        str(_scriptPath("prepareSearchGold.py")),
        "--input",
        str(rawPath),
        "--labels",
        str(reviewedLabels),
        "--out",
        str(goldPath),
        "--summary",
        str(goldSummary),
        "--min-rows",
        str(minRows),
        "--required-targets",
        requiredTargets,
        "--fail-on-ineligible",
    ]
    phase = _runPhase("prepareGold", prepareCmd)
    phases.append(phase)
    if phase["returncode"] != 0:
        return _writeCycleReport(
            cyclePath,
            phases=phases,
            failedPhase="prepareGold",
            paths=_paths(
                reviewedLabels, finalizeSummary, goldPath, goldSummary, qualityReport, missLedger, statusReport
            ),
        )

    qualityCmd = [
        sys.executable,
        "-X",
        "utf8",
        str(_scriptPath("evaluateSearchGold.py")),
        "--gold",
        str(goldPath),
        "--out",
        str(qualityReport),
        "--miss-ledger",
        str(missLedger),
        "--limit",
        str(limit),
        "--scope",
        scope,
        "--min-rows",
        str(minRows),
        "--required-targets",
        requiredTargets,
        "--fail-on-ineligible",
    ]
    if resultsJson:
        qualityCmd.extend(["--results-json", str(resultsJson)])
    phase = _runPhase("evaluateGold", qualityCmd)
    phases.append(phase)
    if phase["returncode"] != 0:
        return _writeCycleReport(
            cyclePath,
            phases=phases,
            failedPhase="evaluateGold",
            paths=_paths(
                reviewedLabels, finalizeSummary, goldPath, goldSummary, qualityReport, missLedger, statusReport
            ),
        )

    if any([remoteEvidence, resultContract, canaryReport, hfRoundTrips, localIndexInfo]):
        statusCmd = [
            sys.executable,
            "-X",
            "utf8",
            str(_scriptPath("evaluateSearchProductizationStatus.py")),
            "--quality-report",
            str(qualityReport),
            "--out",
            str(statusReport),
        ]
        for flag, path in (
            ("--remote-evidence", remoteEvidence),
            ("--result-contract", resultContract),
            ("--canary-report", canaryReport),
            ("--local-index-info", localIndexInfo),
        ):
            if path:
                statusCmd.extend([flag, str(path)])
        for path in hfRoundTrips:
            statusCmd.extend(["--hf-round-trip", str(path)])
        if failOnReleaseNotReady:
            statusCmd.append("--fail-on-release-not-ready")
        phase = _runPhase("productizationStatus", statusCmd)
        phases.append(phase)
        if phase["returncode"] != 0:
            return _writeCycleReport(
                cyclePath,
                phases=phases,
                failedPhase="productizationStatus",
                paths=_paths(
                    reviewedLabels,
                    finalizeSummary,
                    goldPath,
                    goldSummary,
                    qualityReport,
                    missLedger,
                    statusReport,
                ),
            )

    return _writeCycleReport(
        cyclePath,
        phases=phases,
        failedPhase="",
        paths=_paths(reviewedLabels, finalizeSummary, goldPath, goldSummary, qualityReport, missLedger, statusReport),
    )


def _runPhase(name: str, command: Sequence[str]) -> dict[str, Any]:
    proc = subprocess.run(
        list(command),
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
    )
    return {
        "name": name,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _writeCycleReport(
    path: Path,
    *,
    phases: Sequence[Mapping[str, Any]],
    failedPhase: str,
    paths: Mapping[str, str],
) -> dict[str, Any]:
    report = {
        "valid": not failedPhase,
        "releaseEvidence": False,
        "failedPhase": failedPhase,
        "phases": [dict(phase) for phase in phases],
        "paths": dict(paths),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _paths(
    reviewedLabels: Path,
    finalizeSummary: Path,
    goldPath: Path,
    goldSummary: Path,
    qualityReport: Path,
    missLedger: Path,
    statusReport: Path,
    batchReviewedSheet: Path | None = None,
    batchSummary: Path | None = None,
) -> dict[str, str]:
    paths = {
        "reviewedLabels": str(reviewedLabels),
        "finalizeSummary": str(finalizeSummary),
        "queryLogGold": str(goldPath),
        "queryLogGoldSummary": str(goldSummary),
        "qualityReport": str(qualityReport),
        "missLedger": str(missLedger),
        "productizationStatus": str(statusReport),
    }
    if batchReviewedSheet is not None:
        paths["batchReviewedSheet"] = str(batchReviewedSheet)
    if batchSummary is not None:
        paths["batchSummary"] = str(batchSummary)
    return paths


def _scriptPath(name: str) -> Path:
    return Path(__file__).with_name(name)


if __name__ == "__main__":
    raise SystemExit(main())
