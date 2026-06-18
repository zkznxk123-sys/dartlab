"""Build a reviewer pack from hard-negative search candidate gold.

The input is canonical current-data hard-negative JSONL. The output is a raw
query log, a label template, a decision sheet, and an evidence packet. None of
these files is release evidence until a reviewer sets explicit decisions and
``finalizeSearchReviewLabels.py`` / ``evaluateSearchGold.py`` pass.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, help="hard-negative candidate gold JSON/JSONL path")
    parser.add_argument("--out-dir", required=True, help="review pack output directory")
    parser.add_argument("--results-json", help="optional precomputed search results by query/queryId")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--fail-on-batch-not-ready", action="store_true")
    args = parser.parse_args(argv)

    report = buildHardNegativeReviewPack(
        goldPath=Path(args.gold),
        outDir=Path(args.out_dir),
        resultsJson=Path(args.results_json) if args.results_json else None,
        limit=args.limit,
        scope=args.scope,
        maxCandidates=args.max_candidates,
    )
    print(json.dumps({"valid": report["valid"], "blockers": report["blockers"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    if args.fail_on_batch_not_ready and not report["batchReady"]:
        return 1
    return 0


def buildHardNegativeReviewPack(
    *,
    goldPath: Path,
    outDir: Path,
    resultsJson: Path | None = None,
    limit: int = 10,
    scope: str = "auto",
    maxCandidates: int = 5,
) -> dict[str, Any]:
    """Create reviewer-facing artifacts from candidate hard-negative gold."""
    from dartlab.providers.dart.search.goldLog import buildRawQueryLogEvent, writeGoldLogRows

    rows = _loadRows(goldPath)
    resultsByKey = _loadResultsByKey(resultsJson) if resultsJson else {}
    outDir.mkdir(parents=True, exist_ok=True)

    rawRows: list[dict[str, Any]] = []
    labelRows: list[dict[str, Any]] = []
    resultItems: list[dict[str, Any]] = []
    rowsNeedingManualReview: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        query = str(row.get("query") or "").strip()
        if not query:
            rowsNeedingManualReview.append(_issue(index, row, "missingQuery"))
            continue
        searchRows = _resultsForRow(row, resultsByKey)
        if not searchRows:
            searchRows = _runSearch(query=query, limit=limit, scope=scope)
        event = buildRawQueryLogEvent(
            query=query,
            params={
                "scope": scope,
                "limit": limit,
                "targetKindHint": _targetKind(row),
                "hardNegativeType": row.get("hardNegativeType") or "",
            },
            results=searchRows,
            topK=limit,
        )
        event["queryId"] = str(row.get("queryId") or event["queryId"])
        event["targetKindHint"] = _targetKind(row)
        event["hardNegativeType"] = row.get("hardNegativeType") or ""
        event["forbiddenSourceRefs"] = _sourceRefs(row.get("forbiddenSourceRefs"))
        event["forbiddenSourceFamilies"] = _sourceRefs(row.get("forbiddenSourceFamilies"))
        rawRows.append(event)

        labelRows.append(_labelRow(row, event))
        resultItems.append({"queryId": event["queryId"], "query": query, "results": event.get("topResults") or []})

    rawPath = outDir / "queryLogRaw.hardNegativeReview.jsonl"
    labelsPath = outDir / "queryLogLabels.hardNegative.todo.jsonl"
    resultsPath = outDir / "queryResults.hardNegative.json"
    decisionPath = outDir / "queryLogDecisionSheet.hardNegative.todo.jsonl"
    decisionCsvPath = outDir / "queryLogDecisionSheet.hardNegative.todo.csv"
    decisionSummaryPath = outDir / "queryLogDecisionSheet.hardNegative.summary.json"
    evidencePath = outDir / "queryLogDecisionSheet.hardNegative.evidencePacket.json"
    evidenceMdPath = outDir / "queryLogDecisionSheet.hardNegative.evidencePacket.md"

    writeGoldLogRows(rawPath, rawRows)
    writeGoldLogRows(labelsPath, labelRows)
    _writeJson(resultsPath, resultItems)

    decisionProc = _runDecisionSheet(
        labelsPath=labelsPath,
        decisionPath=decisionPath,
        decisionCsvPath=decisionCsvPath,
        decisionSummaryPath=decisionSummaryPath,
        evidencePath=evidencePath,
        evidenceMdPath=evidenceMdPath,
        resultsPath=resultsPath,
        maxCandidates=maxCandidates,
    )

    decisionSummary = _loadJson(decisionSummaryPath)
    evidencePacket = _loadJson(evidencePath)
    blockers = []
    if not rows:
        blockers.append("noRows")
    if rowsNeedingManualReview:
        blockers.append(f"rowsNeedingManualReview:{len(rowsNeedingManualReview)}")
    if decisionProc["returncode"] != 0:
        blockers.append("decisionSheetFailed")
    if not decisionSummary.get("proposalIntegrityAudit", {}).get("valid", False):
        blockers.extend(decisionSummary.get("proposalIntegrityAudit", {}).get("blockers") or [])
    batchBlockers: list[str] = []
    if evidencePacket.get("valid") is not True:
        batchBlockers.extend(f"evidencePacket:{item}" for item in evidencePacket.get("blockers") or ["invalid"])

    report = {
        "valid": not blockers,
        "batchReady": not batchBlockers,
        "releaseEvidence": False,
        "goldPath": str(goldPath),
        "totalRows": len(rows),
        "rawRows": len(rawRows),
        "labelRows": len(labelRows),
        "coverageByKind": _coverage(labelRows, key="targetKindHint"),
        "coverageByHardNegativeType": _coverage(labelRows, key="hardNegativeType"),
        "decisionSheet": decisionSummary,
        "evidencePacket": {
            "valid": evidencePacket.get("valid"),
            "evidenceReadyRows": evidencePacket.get("evidenceReadyRows"),
            "missingEvidenceRows": evidencePacket.get("missingEvidenceRows"),
            "falseAcceptRows": evidencePacket.get("falseAcceptRows"),
            "blockers": evidencePacket.get("blockers") or [],
        },
        "rowsNeedingManualReview": rowsNeedingManualReview[:50],
        "blockers": blockers,
        "batchBlockers": batchBlockers,
        "paths": {
            "rawLog": str(rawPath),
            "labelTemplate": str(labelsPath),
            "resultsJson": str(resultsPath),
            "decisionSheet": str(decisionPath),
            "decisionSheetCsv": str(decisionCsvPath),
            "decisionSummary": str(decisionSummaryPath),
            "evidencePacket": str(evidencePath),
            "evidenceMarkdown": str(evidenceMdPath),
            "report": str(outDir / "hardNegativeReviewPack.json"),
        },
        "nextStep": (
            "Review queryLogDecisionSheet.hardNegative.todo.csv/jsonl, set reviewDecision and reviewer, "
            "then run finalizeSearchReviewLabels.py and evaluateSearchGold.py. This pack is not release evidence."
        ),
    }
    _writeJson(outDir / "hardNegativeReviewPack.json", report)
    return report


def _labelRow(row: Mapping[str, Any], event: Mapping[str, Any]) -> dict[str, Any]:
    target = _targetKind(row)
    expectedAnswerable = _expectedAnswerable(row)
    refs = _sourceRefs(row.get("expectedSourceRefs") or row.get("expectedSourceRef"))
    label: dict[str, Any] = {
        "queryId": event.get("queryId") or row.get("queryId") or "",
        "query": row.get("query") or "",
        "targetKind": "",
        "expectedAnswerable": "",
        "expectedSourceRef": "",
        "expectedSourceRefs": "",
        "goldOrigin": "userLog",
        "reviewStatus": "draft",
        "targetKindHint": "noAnswer" if expectedAnswerable is False else target,
        "hardNegativeType": row.get("hardNegativeType") or "",
        "forbiddenSourceRefs": _sourceRefs(row.get("forbiddenSourceRefs")),
        "forbiddenSourceFamilies": _sourceRefs(row.get("forbiddenSourceFamilies")),
        "distractorSourceRefs": _sourceRefs(row.get("distractorSourceRefs")),
        "sourceDataAsOf": row.get("sourceDataAsOf") or "",
        "reviewerNote": "",
        "topResults": list(event.get("topResults") or [])[:10],
        "reviewInstruction": (
            "Verify the proposed expectedSourceRef/noAnswer against top evidence and forbidden refs. "
            "Only explicit reviewDecision+reviewer can become release gold."
        ),
    }
    if expectedAnswerable is False:
        label.update(
            {
                "proposedTargetKind": "noAnswer",
                "proposedExpectedAnswerable": False,
                "proposedReviewAction": "verifyNoAnswerThenSetExpectedAnswerableFalse",
                "proposedLabelReason": "hardNegativeCandidateExpectedNoAnswer",
            }
        )
        return label
    label.update(
        {
            "proposedTargetKind": target,
            "proposedExpectedAnswerable": True,
            "proposedExpectedSourceRef": refs[0] if refs else "",
            "proposedExpectedSourceRefs": refs,
            "proposedReviewAction": "verifyProposalThenCopyToExpectedFields",
            "proposedLabelReason": "hardNegativeCandidateExpectedSourceRef",
            "candidateSourceRefs": _candidateSourceRefs(event, refs),
        }
    )
    return label


def _runSearch(*, query: str, limit: int, scope: str) -> list[dict[str, Any]]:
    import dartlab

    return dartlab.search(query, limit=limit, scope=scope).to_dicts()


def _runDecisionSheet(
    *,
    labelsPath: Path,
    decisionPath: Path,
    decisionCsvPath: Path,
    decisionSummaryPath: Path,
    evidencePath: Path,
    evidenceMdPath: Path,
    resultsPath: Path,
    maxCandidates: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-X",
        "utf8",
        str(Path(__file__).with_name("buildSearchReviewDecisionSheet.py")),
        "--labels",
        str(labelsPath),
        "--out",
        str(decisionPath),
        "--summary",
        str(decisionSummaryPath),
        "--csv-out",
        str(decisionCsvPath),
        "--results-json",
        str(resultsPath),
        "--evidence-out",
        str(evidencePath),
        "--evidence-md-out",
        str(evidenceMdPath),
        "--max-candidates",
        str(maxCandidates),
        "--fail-on-proposal-errors",
    ]
    proc = subprocess.run(
        command,
        cwd=Path.cwd(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=180,
    )
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def _loadRows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, Mapping)]
    if isinstance(data, Mapping):
        for key in ("rows", "gold", "queryLogGold"):
            values = data.get(key)
            if isinstance(values, list):
                return [dict(row) for row in values if isinstance(row, Mapping)]
    raise ValueError(f"unsupported hard-negative gold shape: {path}")


def _loadResultsByKey(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[dict[str, Any]]] = {}
    if isinstance(data, Mapping):
        for key, rows in data.items():
            if isinstance(rows, list):
                out[str(key)] = [dict(row) for row in rows if isinstance(row, Mapping)]
        return out
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, Mapping):
                continue
            rows = [dict(row) for row in item.get("results", []) if isinstance(row, Mapping)]
            for key in (item.get("queryId"), item.get("id"), item.get("query")):
                if key:
                    out[str(key)] = rows
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _resultsForRow(row: Mapping[str, Any], resultsByKey: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    for key in (row.get("queryId"), row.get("id"), row.get("query")):
        if key and str(key) in resultsByKey:
            return [dict(item) for item in resultsByKey[str(key)]]
    return []


def _targetKind(row: Mapping[str, Any]) -> str:
    target = str(row.get("targetKind") or row.get("target") or "").strip()
    if target:
        return target
    sourceRef = str(row.get("expectedSourceRef") or "")
    if sourceRef.startswith("news:"):
        return "news"
    if sourceRef.startswith("edgar:"):
        return "edgar"
    if sourceRef.startswith("dart:"):
        return "filing"
    return "noAnswer" if _expectedAnswerable(row) is False else ""


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
    return str(row.get("targetKind") or row.get("target") or "").strip() != "noAnswer"


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


def _candidateSourceRefs(event: Mapping[str, Any], proposedRefs: Sequence[str]) -> list[str]:
    out: list[str] = []
    for ref in list(proposedRefs) + [str(item) for item in event.get("topSourceRefs") or []]:
        if ref and ref not in out:
            out.append(ref)
    return out


def _coverage(rows: Iterable[Mapping[str, Any]], *, key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        out[value] = out.get(value, 0) + 1
    return out


def _issue(index: int, row: Mapping[str, Any], reason: str) -> dict[str, Any]:
    return {
        "rowIndex": index,
        "queryId": str(row.get("queryId") or ""),
        "query": str(row.get("query") or ""),
        "reason": reason,
    }


def _loadJson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _writeJson(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
