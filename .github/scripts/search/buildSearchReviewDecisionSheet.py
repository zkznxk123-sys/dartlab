"""Build a compact decision sheet from search review-pack labels.

The output keeps official gold fields blank and carries only proposal fields,
top candidate summaries, and empty reviewer decision columns. It is meant to
make 100+ row review practical without turning generated proposals into
release evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DECISION_COLUMNS: tuple[str, ...] = (
    "queryId",
    "query",
    "targetKindHint",
    "reviewDecision",
    "suggestedReviewDecision",
    "reviewer",
    "reviewerNote",
    "targetKind",
    "expectedAnswerable",
    "expectedSourceRef",
    "expectedSourceRefs",
    "proposedTargetKind",
    "proposedExpectedAnswerable",
    "proposedExpectedSourceRef",
    "proposedExpectedSourceRefs",
    "proposedReviewAction",
    "proposedLabelReason",
    "candidateSourceRefs",
    "candidateSummaries",
    "topSource",
    "topSourceRef",
    "topCompanyName",
    "topStockCode",
    "topReportName",
    "topTitle",
    "topDataAsOf",
    "topUrl",
    "topAnswerable",
    "topNotAnswerableReason",
    "topScore",
)
ACCEPT_PROPOSAL_DECISIONS = {"acceptProposal", "accept-proposal", "verifiedProposal", "verified-proposal"}
VERIFY_NO_ANSWER_DECISIONS = {"verifiedNoAnswer", "verified-no-answer", "acceptNoAnswer", "accept-no-answer"}
MANUAL_DECISIONS = {"manual", "manualLabel", "manual-label"}
KNOWN_DECISIONS = ACCEPT_PROPOSAL_DECISIONS | VERIFY_NO_ANSWER_DECISIONS | MANUAL_DECISIONS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", action="append", default=[], help="review label JSON/JSONL path")
    parser.add_argument("--out", required=True, help="compact decision sheet JSONL/JSON output path")
    parser.add_argument("--summary", help="summary JSON output path")
    parser.add_argument("--csv-out", help="optional CSV mirror for spreadsheet review")
    parser.add_argument("--results-json", help="optional full query results JSON for evidence packet output")
    parser.add_argument("--evidence-out", help="optional review evidence packet JSON output")
    parser.add_argument("--evidence-md-out", help="optional review evidence packet Markdown output")
    parser.add_argument("--max-candidates", type=int, default=3, help="number of top candidates to preserve")
    parser.add_argument("--fail-on-incomplete", action="store_true", help="fail when decisions/reviewers are missing")
    parser.add_argument("--fail-on-proposal-errors", action="store_true", help="fail when proposed fields are invalid")
    parser.add_argument("--fail-on-evidence-issues", action="store_true", help="fail when evidence packet has blockers")
    args = parser.parse_args(argv)

    if not args.labels:
        raise SystemExit("--labels is required")

    rows = loadReviewRows(args.labels)
    sheetRows, summary = buildReviewDecisionSheet(
        rows,
        maxCandidates=args.max_candidates,
        failOnIncomplete=args.fail_on_incomplete,
        failOnProposalErrors=args.fail_on_proposal_errors,
    )
    out = Path(args.out)
    if out.suffix.lower() == ".json":
        _writeJson(out, {"rows": sheetRows, "summary": summary})
    else:
        _writeJsonl(out, sheetRows)
    if args.summary:
        _writeJson(Path(args.summary), summary)
    if args.csv_out:
        _writeCsv(Path(args.csv_out), sheetRows)
    evidencePacket: dict[str, Any] | None = None
    if args.evidence_out or args.evidence_md_out:
        evidencePacket = buildReviewEvidencePacket(
            sheetRows,
            resultsByQuery=_loadResultsByQuery(Path(args.results_json)) if args.results_json else {},
            maxCandidates=args.max_candidates,
        )
        if args.evidence_out:
            _writeJson(Path(args.evidence_out), evidencePacket)
        if args.evidence_md_out:
            Path(args.evidence_md_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.evidence_md_out).write_text(_evidenceMarkdown(evidencePacket), encoding="utf-8")

    print(json.dumps({"valid": summary["valid"], "rows": summary["totalRows"]}, ensure_ascii=False))
    if args.fail_on_evidence_issues and evidencePacket and evidencePacket["blockers"]:
        return 1
    return 0 if summary["valid"] else 1


def buildReviewDecisionSheet(
    rows: Iterable[Mapping[str, Any]],
    *,
    maxCandidates: int = 3,
    failOnIncomplete: bool = False,
    failOnProposalErrors: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Create compact reviewer decision rows without producing release labels."""
    rowList = [dict(row) for row in rows]
    sheetRows = [_compactRow(row, maxCandidates=max(1, maxCandidates)) for row in rowList]
    needsInspection = [row for row in sheetRows if str(row.get("proposedReviewAction") or "").startswith("inspect")]
    suggestedCounts: dict[str, int] = {}
    for row in sheetRows:
        decision = str(row.get("suggestedReviewDecision") or "")
        suggestedCounts[decision] = suggestedCounts.get(decision, 0) + 1
    decisionAudit = _decisionAudit(sheetRows)
    proposalAudit = _proposalIntegrityAudit(rowList, sheetRows)

    blockers: list[str] = []
    if not sheetRows:
        blockers.append("noRows")
    if failOnIncomplete:
        blockers.extend(decisionAudit["blockers"])
    if failOnProposalErrors:
        blockers.extend(proposalAudit["blockers"])

    summary = {
        "valid": not blockers,
        "releaseEvidence": False,
        "totalRows": len(sheetRows),
        "proposedAnswerableRows": sum(1 for row in sheetRows if row.get("proposedExpectedAnswerable") is True),
        "proposedNoAnswerRows": sum(1 for row in sheetRows if row.get("proposedExpectedAnswerable") is False),
        "needsInspectionRows": len(needsInspection),
        "suggestedDecisionCounts": suggestedCounts,
        "decisionAudit": decisionAudit,
        "proposalIntegrityAudit": proposalAudit,
        "maxCandidates": max(1, maxCandidates),
        "blockers": blockers,
        "nextStep": (
            "Review this compact sheet, set reviewDecision/reviewer, and only then run "
            "finalizeSearchReviewLabels.py. suggestedReviewDecision is not a release label."
        ),
    }
    return sheetRows, summary


def _proposalIntegrityAudit(
    sourceRows: Sequence[Mapping[str, Any]], sheetRows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    invalidRows: list[dict[str, Any]] = []
    for index, row in enumerate(sheetRows):
        raw = sourceRows[index] if index < len(sourceRows) else row
        reasons = _proposalIntegrityReasons(raw, row)
        if reasons:
            invalidRows.append(
                {
                    "rowIndex": index,
                    "query": str(row.get("query") or ""),
                    "queryId": str(row.get("queryId") or ""),
                    "reasons": reasons,
                }
            )
    blockers = [f"proposalInvalidRows:{len(invalidRows)}"] if invalidRows else []
    return {
        "valid": not blockers,
        "invalidRows": len(invalidRows),
        "blockers": blockers,
        "examples": invalidRows[:20],
    }


def _proposalIntegrityReasons(raw: Mapping[str, Any], row: Mapping[str, Any]) -> list[str]:
    reasons: list[str] = []
    proposedAnswerable = _boolValue(row.get("proposedExpectedAnswerable"))
    target = str(row.get("proposedTargetKind") or row.get("targetKindHint") or "").strip()
    refs = _sourceRefs(row.get("proposedExpectedSourceRefs") or row.get("proposedExpectedSourceRef"))
    candidateRefs = _sourceRefs(row.get("candidateSourceRefs"))

    if proposedAnswerable is True:
        if not target or target == "noAnswer":
            reasons.append("answerableProposalMissingTarget")
        if not refs:
            reasons.append("answerableProposalMissingSourceRef")
        elif candidateRefs and refs[0] not in candidateRefs:
            reasons.append("proposalSourceRefNotInCandidates")
        for ref in refs:
            if not _sourceRefMatchesTarget(ref, target):
                reasons.append("proposalSourceRefTargetMismatch")
                break
    elif proposedAnswerable is False:
        if target and target != "noAnswer":
            reasons.append("noAnswerProposalTargetMismatch")
        topResults = raw.get("topResults")
        if isinstance(topResults, list) and any(
            _isAnswerableResult(item) for item in topResults if isinstance(item, Mapping)
        ):
            reasons.append("noAnswerProposalHasAnswerableTopResult")
    elif str(row.get("proposedReviewAction") or "").startswith("inspect"):
        return reasons
    else:
        reasons.append("proposalMissingExpectedAnswerable")

    return list(dict.fromkeys(reasons))


def _sourceRefMatchesTarget(sourceRef: str, target: str) -> bool:
    if target == "news":
        return sourceRef.startswith("news:")
    if target == "edgar":
        return sourceRef.startswith("edgar:")
    if target == "filing":
        return sourceRef.startswith("dart:")
    return True


def _sourceRefs(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, str):
        values.extend(_splitRefs(value))
    elif isinstance(value, Sequence):
        values.extend(str(item).strip() for item in value if str(item).strip())
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
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


def _isAnswerableResult(row: Mapping[str, Any]) -> bool:
    value = row.get("answerable")
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return True
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "n"}
    return bool(value)


def _decisionAudit(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    decisionCounts: dict[str, int] = {}
    undecidedRows: list[dict[str, Any]] = []
    missingReviewerRows: list[dict[str, Any]] = []
    unknownDecisionRows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        decision = str(row.get("reviewDecision") or "").strip()
        if not decision:
            undecidedRows.append(_rowIssue(index, row, "missingReviewDecision"))
            continue
        decisionCounts[decision] = decisionCounts.get(decision, 0) + 1
        if decision not in KNOWN_DECISIONS:
            unknownDecisionRows.append(_rowIssue(index, row, f"unknownReviewDecision:{decision}"))
        if not str(row.get("reviewer") or row.get("labeler") or "").strip():
            missingReviewerRows.append(_rowIssue(index, row, "missingReviewer"))

    blockers: list[str] = []
    if undecidedRows:
        blockers.append(f"undecidedRows:{len(undecidedRows)}")
    if missingReviewerRows:
        blockers.append(f"missingReviewerRows:{len(missingReviewerRows)}")
    if unknownDecisionRows:
        blockers.append(f"unknownDecisionRows:{len(unknownDecisionRows)}")

    return {
        "reviewComplete": not blockers,
        "decidedRows": sum(decisionCounts.values()),
        "undecidedRows": len(undecidedRows),
        "missingReviewerRows": len(missingReviewerRows),
        "unknownDecisionRows": len(unknownDecisionRows),
        "decisionCounts": decisionCounts,
        "blockers": blockers,
        "examples": {
            "undecidedRows": undecidedRows[:20],
            "missingReviewerRows": missingReviewerRows[:20],
            "unknownDecisionRows": unknownDecisionRows[:20],
        },
    }


def _rowIssue(index: int, row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "rowIndex": index,
        "query": str(row.get("query") or ""),
        "queryId": str(row.get("queryId") or ""),
        "reason": reason,
    }


def loadReviewRows(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Load JSON, JSONL, or CSV review rows."""
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


def _compactRow(row: Mapping[str, Any], *, maxCandidates: int) -> dict[str, Any]:
    candidates = _candidateRows(row, maxCandidates=maxCandidates)
    top = candidates[0] if candidates else {}
    out = {key: "" for key in DECISION_COLUMNS}
    for key in ("queryId", "query", "targetKindHint", "reviewDecision", "reviewer", "reviewerNote"):
        value = row.get(key)
        if value not in (None, ""):
            out[key] = value
    for key in (
        "targetKind",
        "expectedAnswerable",
        "expectedSourceRef",
        "expectedSourceRefs",
        "proposedTargetKind",
        "proposedExpectedAnswerable",
        "proposedExpectedSourceRef",
        "proposedExpectedSourceRefs",
        "proposedReviewAction",
        "proposedLabelReason",
    ):
        if key in row:
            out[key] = row.get(key)
    out["suggestedReviewDecision"] = _suggestedDecision(row)
    out["candidateSourceRefs"] = _candidateSourceRefs(row, candidates, maxCandidates=maxCandidates)
    out["candidateSummaries"] = _candidateSummaries(candidates)
    out.update(
        {
            "topSource": top.get("source", ""),
            "topSourceRef": top.get("sourceRef", ""),
            "topCompanyName": top.get("companyName", ""),
            "topStockCode": top.get("stockCode", ""),
            "topReportName": top.get("reportName", ""),
            "topTitle": top.get("title", ""),
            "topDataAsOf": top.get("dataAsOf", ""),
            "topUrl": top.get("url", ""),
            "topAnswerable": top.get("answerable", ""),
            "topNotAnswerableReason": top.get("notAnswerableReason", ""),
            "topScore": top.get("score", ""),
        }
    )
    return out


def _suggestedDecision(row: Mapping[str, Any]) -> str:
    action = str(row.get("proposedReviewAction") or "")
    if action.startswith("inspect"):
        return ""
    if row.get("proposedExpectedAnswerable") is False:
        return "verifiedNoAnswer"
    if row.get("proposedExpectedSourceRef"):
        return "acceptProposal"
    return ""


def _candidateRows(row: Mapping[str, Any], *, maxCandidates: int) -> list[dict[str, Any]]:
    raw = row.get("topResults")
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in raw[:maxCandidates]:
        if not isinstance(item, Mapping):
            continue
        rows.append(
            {
                "source": _scalar(item.get("source")),
                "sourceRef": _scalar(item.get("sourceRef")),
                "companyName": _scalar(item.get("companyName")),
                "stockCode": _scalar(item.get("stockCode")),
                "reportName": _scalar(item.get("reportName")),
                "title": _scalar(item.get("title")),
                "dataAsOf": _scalar(item.get("dataAsOf")),
                "url": _scalar(item.get("url")),
                "answerable": item.get("answerable", ""),
                "notAnswerableReason": _scalar(item.get("notAnswerableReason")),
                "score": item.get("score", ""),
            }
        )
    return rows


def buildReviewEvidencePacket(
    rows: Sequence[Mapping[str, Any]],
    *,
    resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]],
    maxCandidates: int = 3,
) -> dict[str, Any]:
    """Build a reviewer-facing evidence packet from decision rows and full results."""
    packetRows: list[dict[str, Any]] = []
    missingEvidenceRows: list[dict[str, Any]] = []
    falseAcceptRows: list[dict[str, Any]] = []
    sourceCounts: dict[str, int] = {}
    readyRows = 0
    for index, row in enumerate(rows):
        query = str(row.get("query") or "")
        queryId = str(row.get("queryId") or "")
        results = _resultsForRow(row, resultsByQuery)
        proposedRefs = _sourceRefs(row.get("proposedExpectedSourceRefs") or row.get("proposedExpectedSourceRef"))
        proposedAnswerable = _boolValue(row.get("proposedExpectedAnswerable"))
        topEvidence = [_projectEvidenceResult(item) for item in results[: max(1, maxCandidates)]]
        proposedEvidence = [item for item in topEvidence if item.get("sourceRef") in proposedRefs]
        for item in topEvidence:
            source = str(item.get("source") or "")
            if source:
                sourceCounts[source] = sourceCounts.get(source, 0) + 1
        issues: list[str] = []
        if proposedAnswerable is True and not proposedEvidence:
            issues.append("proposalSourceRefMissingFromEvidence")
        if proposedAnswerable is False and any(_isAnswerableResult(item) for item in topEvidence):
            issues.append("noAnswerEvidenceHasAnswerableTopResult")
            falseAcceptRows.append(_rowIssue(index, row, "noAnswerEvidenceHasAnswerableTopResult"))
        if not topEvidence and proposedAnswerable is not False:
            issues.append("missingQueryResults")
        if issues:
            missingEvidenceRows.append(_rowIssue(index, row, ",".join(issues)))
        else:
            readyRows += 1
        packetRows.append(
            {
                "rowIndex": index,
                "queryId": queryId,
                "query": query,
                "suggestedReviewDecision": row.get("suggestedReviewDecision") or "",
                "proposedTargetKind": row.get("proposedTargetKind") or row.get("targetKindHint") or "",
                "proposedExpectedAnswerable": proposedAnswerable,
                "proposedExpectedSourceRefs": proposedRefs,
                "topEvidence": topEvidence,
                "proposedEvidence": proposedEvidence,
                "issues": issues,
            }
        )
    blockers = [f"evidenceRowsNotReady:{len(missingEvidenceRows)}"] if missingEvidenceRows else []
    return {
        "valid": not blockers,
        "releaseEvidence": False,
        "totalRows": len(rows),
        "evidenceReadyRows": readyRows,
        "missingEvidenceRows": len(missingEvidenceRows),
        "falseAcceptRows": len(falseAcceptRows),
        "sourceCounts": sourceCounts,
        "blockers": blockers,
        "examples": missingEvidenceRows[:20],
        "rows": packetRows,
        "nextStep": "Reviewer inspects this packet, then writes reviewDecision/reviewer or runs batch approval.",
    }


def _resultsForRow(
    row: Mapping[str, Any],
    resultsByQuery: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    queryId = str(row.get("queryId") or "").strip()
    query = str(row.get("query") or "").strip()
    raw = resultsByQuery.get(queryId) if queryId else None
    if raw is None:
        raw = resultsByQuery.get(query, [])
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _projectEvidenceResult(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source": _scalar(row.get("source")),
        "sourceRef": _scalar(row.get("sourceRef")),
        "companyName": _scalar(row.get("companyName") or row.get("corp_name")),
        "stockCode": _scalar(row.get("stockCode") or row.get("stock_code")),
        "reportName": _scalar(row.get("reportName") or row.get("report_nm")),
        "title": _scalar(row.get("title") or row.get("section_title")),
        "dataAsOf": _scalar(row.get("dataAsOf") or row.get("sourceDataAsOf")),
        "url": _scalar(row.get("url") or row.get("dartUrl")),
        "answerable": row.get("answerable", ""),
        "notAnswerableReason": _scalar(row.get("notAnswerableReason")),
        "score": row.get("score", ""),
        "snippet": _truncate(_scalar(row.get("snippet") or row.get("evidenceText") or row.get("text")), 360),
    }


def _loadResultsByQuery(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(query): [dict(row) for row in rows if isinstance(row, Mapping)] for query, rows in data.items()}
    if isinstance(data, list):
        out: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            if not isinstance(item, Mapping):
                continue
            rows = [dict(row) for row in item.get("results", []) if isinstance(row, Mapping)]
            query = str(item.get("query") or "")
            queryId = str(item.get("queryId") or item.get("id") or "")
            if query:
                out[query] = rows
            if queryId:
                out[queryId] = rows
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _evidenceMarkdown(packet: Mapping[str, Any]) -> str:
    lines = [
        "# Search Review Evidence Packet",
        "",
        f"- totalRows: {packet.get('totalRows')}",
        f"- evidenceReadyRows: {packet.get('evidenceReadyRows')}",
        f"- blockers: {', '.join(str(item) for item in packet.get('blockers') or []) or 'none'}",
        "",
    ]
    for row in packet.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        lines.extend(
            [
                f"## {row.get('rowIndex')}. {row.get('query')}",
                "",
                f"- decision: {row.get('suggestedReviewDecision')}",
                f"- proposedTargetKind: {row.get('proposedTargetKind')}",
                f"- proposedSourceRefs: {', '.join(str(item) for item in row.get('proposedExpectedSourceRefs') or [])}",
                f"- issues: {', '.join(str(item) for item in row.get('issues') or []) or 'none'}",
                "",
            ]
        )
        for item in row.get("topEvidence") or []:
            if not isinstance(item, Mapping):
                continue
            lines.extend(
                [
                    f"- {item.get('sourceRef')} | {item.get('companyName')} | {item.get('reportName') or item.get('title')}",
                    f"  - answerable: {item.get('answerable')} / reason: {item.get('notAnswerableReason')}",
                    f"  - url: {item.get('url')}",
                    f"  - snippet: {item.get('snippet')}",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _truncate(value: str, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _candidateSourceRefs(
    row: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]], *, maxCandidates: int
) -> list[str]:
    values: list[str] = []
    raw = row.get("candidateSourceRefs")
    if isinstance(raw, str):
        values.extend(_splitRefs(raw))
    elif isinstance(raw, Sequence):
        values.extend(str(item).strip() for item in raw if str(item).strip())
    values.extend(str(item.get("sourceRef") or "").strip() for item in candidates if item.get("sourceRef"))
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out[: max(1, maxCandidates)]


def _candidateSummaries(candidates: Sequence[Mapping[str, Any]]) -> list[str]:
    out: list[str] = []
    for index, item in enumerate(candidates, start=1):
        parts = [
            str(index),
            str(item.get("sourceRef") or ""),
            str(item.get("companyName") or ""),
            str(item.get("stockCode") or ""),
            str(item.get("reportName") or item.get("title") or ""),
        ]
        out.append(" | ".join(part.strip() for part in parts if part not in ("", None)))
    return out


def _splitRefs(value: str) -> list[str]:
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = []
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    sep = "|" if "|" in text and "," not in text else ","
    return [part.strip() for part in text.split(sep) if part.strip()]


def _scalar(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return str(value)


def _writeJsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _writeJson(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _writeCsv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(DECISION_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csvValue(row.get(key, "")) for key in DECISION_COLUMNS})


def _csvValue(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
