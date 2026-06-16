"""Apply explicit batch decisions to a search review decision sheet.

This is a reviewer workflow accelerator. It never creates release evidence by
itself: it only fills ``reviewDecision``/``reviewer`` on rows that already have
clean suggested decisions. ``finalizeSearchReviewLabels.py`` and the real
quality cycle still decide whether the reviewed labels become release evidence.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", required=True, help="decision sheet JSON/JSONL/CSV path")
    parser.add_argument("--out", help="reviewed decision sheet JSONL output path")
    parser.add_argument("--summary", help="summary JSON output path")
    parser.add_argument("--reviewer", default="", help="reviewer id required unless --dry-run")
    parser.add_argument("--reviewed-at", default="", help="review timestamp; defaults to current UTC time")
    parser.add_argument(
        "--accept-suggested", action="store_true", help="copy suggestedReviewDecision into reviewDecision"
    )
    parser.add_argument("--overwrite", action="store_true", help="overwrite existing decisions")
    parser.add_argument(
        "--quality-ceiling", help="optional searchProposalQualityCeiling.json or qualityCeilingReport.json"
    )
    parser.add_argument("--require-metric-eligible", action="store_true")
    parser.add_argument("--evidence-packet", help="optional review evidence packet JSON")
    parser.add_argument("--require-evidence-ready", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="only validate whether batch approval is possible")
    args = parser.parse_args(argv)

    if not args.accept_suggested:
        raise SystemExit("--accept-suggested is required")
    if not args.dry_run and not args.out:
        raise SystemExit("--out is required unless --dry-run")
    if not args.dry_run and not args.reviewer.strip():
        raise SystemExit("--reviewer is required unless --dry-run")

    rows = _decisionSheetModule().loadReviewRows([args.sheet])
    qualityCeiling = _loadQualityCeiling(Path(args.quality_ceiling)) if args.quality_ceiling else {}
    evidencePacket = _loadEvidencePacket(Path(args.evidence_packet)) if args.evidence_packet else {}
    reviewedRows, summary = applyBatchSuggestedDecisions(
        rows,
        reviewer=args.reviewer,
        reviewedAt=args.reviewed_at,
        overwrite=args.overwrite,
        dryRun=args.dry_run,
        qualityCeiling=qualityCeiling,
        requireMetricEligible=args.require_metric_eligible,
        evidencePacket=evidencePacket,
        requireEvidenceReady=args.require_evidence_ready,
    )
    if args.out and not args.dry_run:
        _writeJsonl(Path(args.out), reviewedRows)
    if args.summary:
        _writeJson(Path(args.summary), summary)
    print(json.dumps({"valid": summary["valid"], "readyRows": summary["readyRows"]}, ensure_ascii=False))
    return 0 if summary["valid"] else 1


def applyBatchSuggestedDecisions(
    rows: Sequence[Mapping[str, Any]],
    *,
    reviewer: str = "",
    reviewedAt: str = "",
    overwrite: bool = False,
    dryRun: bool = False,
    qualityCeiling: Mapping[str, Any] | None = None,
    requireMetricEligible: bool = False,
    evidencePacket: Mapping[str, Any] | None = None,
    requireEvidenceReady: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fill suggested decisions when batch approval prerequisites are met."""
    reviewerId = reviewer.strip()
    reviewedAtValue = reviewedAt or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    outRows: list[dict[str, Any]] = []
    rowIssues: list[dict[str, Any]] = []
    readyRows = 0
    alreadyDecidedRows = 0
    wouldDecideRows = 0

    for index, row in enumerate(rows):
        out = dict(row)
        existingDecision = str(out.get("reviewDecision") or "").strip()
        suggested = str(out.get("suggestedReviewDecision") or "").strip()
        if existingDecision and not overwrite:
            alreadyDecidedRows += 1
            if not str(out.get("reviewer") or out.get("labeler") or "").strip():
                rowIssues.append(_rowIssue(index, out, "missingReviewerForExistingDecision"))
            outRows.append(out)
            continue
        reasons = _rowReadinessIssues(out, suggested=suggested)
        if reasons:
            rowIssues.append(_rowIssue(index, out, ",".join(reasons)))
            outRows.append(out)
            continue
        readyRows += 1
        wouldDecideRows += 1
        if not dryRun:
            out["reviewDecision"] = suggested
            out["reviewer"] = reviewerId
            out["reviewedAt"] = reviewedAtValue
            note = str(out.get("reviewerNote") or "").strip()
            marker = "batchAcceptedSuggested"
            out["reviewerNote"] = f"{note}; {marker}" if note else marker
        outRows.append(out)

    qualitySummary = _qualityCeilingSummary(qualityCeiling or {})
    evidenceSummary = _evidencePacketSummary(evidencePacket or {}, expectedRows=len(rows))
    blockers: list[str] = []
    if rowIssues:
        blockers.append(f"batchRowsNotReady:{len(rowIssues)}")
    if not dryRun and not reviewerId:
        blockers.append("missingReviewer")
    if requireMetricEligible and not qualitySummary.get("metricEligible"):
        blockers.append("qualityCeilingNotMetricEligible")
    if qualitySummary.get("releaseEvidence") is True:
        blockers.append("qualityCeilingMustNotBeReleaseEvidence")
    if requireEvidenceReady and not evidenceSummary.get("ready"):
        blockers.extend(evidenceSummary.get("blockers") or ["evidencePacketNotReady"])

    summary = {
        "valid": not blockers,
        "releaseEvidence": False,
        "mode": "acceptSuggested",
        "dryRun": dryRun,
        "totalRows": len(rows),
        "readyRows": readyRows,
        "wouldDecideRows": wouldDecideRows,
        "alreadyDecidedRows": alreadyDecidedRows,
        "rowIssues": rowIssues[:50],
        "qualityCeiling": qualitySummary,
        "evidencePacket": evidenceSummary,
        "blockers": blockers,
        "nextStep": (
            "Inspect the sheet and run this command without --dry-run and with --reviewer, then run "
            "finalizeSearchReviewLabels.py or runSearchQualityCycle.py --batch-accept-suggested."
            if dryRun
            else "Run finalizeSearchReviewLabels.py, then runSearchQualityCycle.py for release evidence."
        ),
    }
    return outRows, summary


def _rowReadinessIssues(row: Mapping[str, Any], *, suggested: str) -> list[str]:
    reasons: list[str] = []
    if not suggested:
        reasons.append("missingSuggestedReviewDecision")
    action = str(row.get("proposedReviewAction") or "")
    if action.startswith("inspect"):
        reasons.append("proposalNeedsInspection")
    proposedAnswerable = _boolValue(row.get("proposedExpectedAnswerable"))
    target = str(row.get("proposedTargetKind") or row.get("targetKindHint") or "").strip()
    refs = _sourceRefs(row.get("proposedExpectedSourceRefs") or row.get("proposedExpectedSourceRef"))
    if suggested == "acceptProposal":
        if proposedAnswerable is not True:
            reasons.append("acceptProposalWithoutAnswerableProposal")
        if not target or target == "noAnswer":
            reasons.append("acceptProposalMissingTarget")
        if not refs:
            reasons.append("acceptProposalMissingSourceRef")
    if suggested == "verifiedNoAnswer":
        if proposedAnswerable is not False:
            reasons.append("verifiedNoAnswerWithoutNoAnswerProposal")
    if suggested and suggested not in {"acceptProposal", "verifiedNoAnswer"}:
        reasons.append(f"unsupportedSuggestedDecision:{suggested}")
    return list(dict.fromkeys(reasons))


def _qualityCeilingSummary(report: Mapping[str, Any]) -> dict[str, Any]:
    if not report:
        return {}
    quality = report.get("qualityReport") if isinstance(report.get("qualityReport"), Mapping) else report
    return {
        "releaseEvidence": bool(report.get("releaseEvidence") or quality.get("releaseEvidence")),
        "metricEligible": bool(quality.get("metricEligible")),
        "invalidProposalRows": _int(report.get("invalidProposalRows"), 0),
        "proxyRows": _int(report.get("proxyRows") or quality.get("totalRows"), 0),
        "blockers": list(quality.get("blockers") or []),
    }


def _evidencePacketSummary(report: Mapping[str, Any], *, expectedRows: int) -> dict[str, Any]:
    if not report:
        return {"ready": False, "blockers": ["evidencePacketMissing"]}
    totalRows = _int(report.get("totalRows"), -1)
    readyRows = _int(report.get("evidenceReadyRows"), -1)
    missingRows = _int(report.get("missingEvidenceRows"), 0)
    falseAcceptRows = _int(report.get("falseAcceptRows"), 0)
    blockers: list[str] = []
    if report.get("valid") is not True:
        blockers.append("evidencePacketInvalid")
    if report.get("releaseEvidence") is True:
        blockers.append("evidencePacketMustNotBeReleaseEvidence")
    if totalRows != expectedRows:
        blockers.append(f"evidencePacketRows:{totalRows}/{expectedRows}")
    if readyRows != expectedRows:
        blockers.append(f"evidencePacketReadyRows:{readyRows}/{expectedRows}")
    if missingRows:
        blockers.append(f"evidencePacketMissingEvidenceRows:{missingRows}")
    if falseAcceptRows:
        blockers.append(f"evidencePacketFalseAcceptRows:{falseAcceptRows}")
    blockers.extend(f"evidencePacketBlocker:{item}" for item in report.get("blockers") or [])
    return {
        "ready": not blockers,
        "valid": bool(report.get("valid")),
        "releaseEvidence": bool(report.get("releaseEvidence")),
        "totalRows": totalRows,
        "evidenceReadyRows": readyRows,
        "missingEvidenceRows": missingRows,
        "falseAcceptRows": falseAcceptRows,
        "sourceCounts": dict(report.get("sourceCounts") or {}),
        "blockers": blockers,
    }


def _loadQualityCeiling(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _loadEvidencePacket(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rowIssue(index: int, row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "rowIndex": index,
        "query": str(row.get("query") or ""),
        "queryId": str(row.get("queryId") or ""),
        "reason": reason,
    }


def _sourceRefs(value: Any) -> list[str]:
    raw: list[str] = []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = []
            if isinstance(data, list):
                raw.extend(str(item).strip() for item in data if str(item).strip())
        else:
            sep = "|" if "|" in text and "," not in text else ","
            raw.extend(part.strip() for part in text.split(sep) if part.strip())
    elif isinstance(value, Sequence):
        raw.extend(str(item).strip() for item in value if str(item).strip())
    out: list[str] = []
    for item in raw:
        if item and item not in out:
            out.append(item)
    return out


def _boolValue(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
    if value in (0, 1):
        return bool(value)
    return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _decisionSheetModule():
    script = Path(__file__).with_name("buildSearchReviewDecisionSheet.py")
    spec = importlib.util.spec_from_file_location("_dartlab_review_decision_sheet", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _writeJson(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _writeJsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
