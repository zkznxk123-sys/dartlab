"""Finalize reviewed search label rows after explicit human decisions.

This script copies proposed review-pack fields into official label fields only
when each row carries an explicit review decision. It is a reviewer workflow
accelerator, not an auto-labeler.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

ACCEPT_PROPOSAL_DECISIONS = {"acceptProposal", "accept-proposal", "verifiedProposal", "verified-proposal"}
VERIFY_NO_ANSWER_DECISIONS = {"verifiedNoAnswer", "verified-no-answer", "acceptNoAnswer", "accept-no-answer"}
MANUAL_DECISIONS = {"manual", "manualLabel", "manual-label"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", action="append", default=[], help="review-pack label JSON/JSONL path")
    parser.add_argument("--out", required=True, help="reviewed label JSONL output path")
    parser.add_argument("--summary", help="summary JSON output path")
    parser.add_argument("--reviewer", default="", help="fallback reviewer id for decided rows")
    parser.add_argument("--reviewed-at", default="", help="fallback reviewedAt value")
    parser.add_argument("--allow-partial", action="store_true", help="allow undecided rows to be skipped")
    args = parser.parse_args(argv)

    if not args.labels:
        raise SystemExit("--labels is required")

    rows = _loadRows(args.labels)
    reviewedRows, summary = finalizeReviewLabels(
        rows,
        reviewer=args.reviewer,
        reviewedAt=args.reviewed_at,
        allowPartial=args.allow_partial,
    )
    _writeJsonl(Path(args.out), reviewedRows)
    if args.summary:
        _writeJson(Path(args.summary), summary)

    print(json.dumps({"valid": summary["valid"], "blockers": summary["blockers"]}, ensure_ascii=False))
    return 0 if summary["valid"] else 1


def finalizeReviewLabels(
    rows: Iterable[Mapping[str, Any]],
    *,
    reviewer: str = "",
    reviewedAt: str = "",
    allowPartial: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert explicitly decided review rows into official reviewed labels."""
    rowList = [dict(row) for row in rows]
    reviewedRows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skippedRows: list[dict[str, Any]] = []
    decisionCounts: dict[str, int] = {}
    reviewedAtValue = reviewedAt or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    for index, row in enumerate(rowList):
        decision = str(row.get("reviewDecision") or "").strip()
        if not decision:
            skippedRows.append(_rowIssue(index, row, "missingReviewDecision"))
            continue
        decisionCounts[decision] = decisionCounts.get(decision, 0) + 1
        try:
            reviewedRows.append(_finalizeOne(row, decision=decision, reviewer=reviewer, reviewedAt=reviewedAtValue))
        except ValueError as exc:
            errors.append(_rowIssue(index, row, str(exc)))

    blockers: list[str] = []
    if errors:
        blockers.append(f"invalidReviewedRows:{len(errors)}")
    if skippedRows and not allowPartial:
        blockers.append(f"undecidedRows:{len(skippedRows)}")

    summary = {
        "valid": not blockers,
        "releaseEvidence": False,
        "totalRows": len(rowList),
        "reviewedRows": len(reviewedRows),
        "skippedRows": skippedRows[:20],
        "errors": errors[:20],
        "blockers": blockers,
        "decisionCounts": decisionCounts,
        "nextStep": (
            "Use this reviewed label file with prepareSearchGold.py together with the raw query log. "
            "This summary is not release evidence; evaluateSearchGold.py and productization status decide release."
        ),
    }
    return reviewedRows, summary


def _finalizeOne(row: Mapping[str, Any], *, decision: str, reviewer: str, reviewedAt: str) -> dict[str, Any]:
    labeler = str(row.get("reviewer") or row.get("labeler") or reviewer or "").strip()
    if not labeler:
        raise ValueError("missingReviewer")

    if decision in ACCEPT_PROPOSAL_DECISIONS:
        out = _fromProposal(row)
    elif decision in VERIFY_NO_ANSWER_DECISIONS:
        out = _fromVerifiedNoAnswer(row)
    elif decision in MANUAL_DECISIONS:
        out = _fromManual(row)
    else:
        raise ValueError(f"unknownReviewDecision:{decision}")

    for key in ("query", "queryId", "reviewerNote"):
        value = row.get(key)
        if value not in (None, ""):
            out[key] = value
    out["goldOrigin"] = str(row.get("goldOrigin") or "userLog")
    out["reviewStatus"] = "reviewed"
    out["reviewDecision"] = decision
    out["labeler"] = labeler
    out["reviewedAt"] = reviewedAt
    return out


def _fromProposal(row: Mapping[str, Any]) -> dict[str, Any]:
    target = str(row.get("proposedTargetKind") or row.get("targetKindHint") or "").strip()
    if not target or target == "noAnswer":
        raise ValueError("proposalMissingAnswerableTarget")
    refs = _sourceRefs(row.get("proposedExpectedSourceRefs") or row.get("proposedExpectedSourceRef"))
    if not refs:
        raise ValueError("proposalMissingExpectedSourceRef")
    return {
        "targetKind": target,
        "expectedAnswerable": True,
        "expectedSourceRef": refs[0],
        "expectedSourceRefs": refs,
    }


def _fromVerifiedNoAnswer(row: Mapping[str, Any]) -> dict[str, Any]:
    proposed = row.get("proposedExpectedAnswerable")
    if proposed not in (False, "false", "False", "0", 0):
        raise ValueError("noAnswerDecisionWithoutNoAnswerProposal")
    return {
        "targetKind": "noAnswer",
        "expectedAnswerable": False,
    }


def _fromManual(row: Mapping[str, Any]) -> dict[str, Any]:
    target = str(row.get("targetKind") or row.get("target") or "").strip()
    if not target:
        raise ValueError("manualMissingTargetKind")
    expectedAnswerable = _expectedAnswerable(row)
    out: dict[str, Any] = {
        "targetKind": target,
        "expectedAnswerable": expectedAnswerable,
    }
    if expectedAnswerable:
        refs = _sourceRefs(row.get("expectedSourceRefs") or row.get("expectedSourceRef"))
        if not refs:
            raise ValueError("manualMissingExpectedSourceRef")
        out["expectedSourceRef"] = refs[0]
        out["expectedSourceRefs"] = refs
    return out


def _expectedAnswerable(row: Mapping[str, Any]) -> bool:
    value = row.get("expectedAnswerable")
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"0", "false", "no", "n"}:
            return False
        if lowered in {"1", "true", "yes", "y"}:
            return True
    return str(row.get("targetKind") or row.get("target") or "") != "noAnswer"


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
        if item not in out:
            out.append(item)
    return out


def _rowIssue(index: int, row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "rowIndex": index,
        "query": str(row.get("query") or ""),
        "queryId": str(row.get("queryId") or ""),
        "reason": reason,
    }


def _loadRows(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        p = Path(path)
        if p.suffix.lower() == ".csv":
            with p.open("r", encoding="utf-8", newline="") as f:
                rows.extend(dict(row) for row in csv.DictReader(f))
            continue
        text = p.read_text(encoding="utf-8")
        if p.suffix.lower() == ".jsonl":
            rows.extend(json.loads(line) for line in text.splitlines() if line.strip())
            continue
        data = json.loads(text) if text.strip() else []
        if isinstance(data, list):
            rows.extend(dict(row) for row in data if isinstance(row, Mapping))
            continue
        if isinstance(data, dict):
            for key in ("rows", "labels", "queryLogLabels"):
                value = data.get(key)
                if isinstance(value, list):
                    rows.extend(dict(row) for row in value if isinstance(row, Mapping))
                    break
            else:
                raise ValueError(f"unsupported labels shape: {p}")
            continue
        raise ValueError(f"unsupported labels shape: {p}")
    return rows


def _writeJsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _writeJson(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
