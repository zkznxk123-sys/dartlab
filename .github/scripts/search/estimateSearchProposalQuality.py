"""Estimate search quality from review-pack proposals without release evidence.

This script turns generated review-pack proposal fields into proxy gold rows
only to measure the current ranking/answerability ceiling. The output is
explicitly non-release: productization status must still require human-reviewed
query-log gold before releaseReady can become true.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

PROXY_GOLD_ORIGIN = "proposalProxy"
PROXY_REVIEW_STATUS = "proposalOnly"
PROXY_LABELER = "search-proposal-quality"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", action="append", default=[], help="raw query-log JSON/JSONL path")
    parser.add_argument("--labels", action="append", default=[], help="review-pack proposal labels JSON/JSONL/CSV")
    parser.add_argument("--results-json", required=True, help="precomputed query result JSON path")
    parser.add_argument("--out-dir", required=True, help="output directory")
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--required-targets", default="filing,news,noAnswer,edgar")
    parser.add_argument("--fail-on-invalid-proposals", action="store_true")
    args = parser.parse_args(argv)

    if not args.labels:
        raise SystemExit("--labels is required")

    report = estimateProposalQuality(
        rawPaths=[Path(path) for path in args.raw],
        labelPaths=[Path(path) for path in args.labels],
        resultsJson=Path(args.results_json),
        outDir=Path(args.out_dir),
        minRows=args.min_rows,
        requiredTargets=[part.strip() for part in args.required_targets.split(",") if part.strip()],
    )
    print(
        json.dumps(
            {
                "valid": report["valid"],
                "metricEligible": report["qualityReport"].get("metricEligible"),
                "invalidProposalRows": report["invalidProposalRows"],
            },
            ensure_ascii=False,
        )
    )
    if args.fail_on_invalid_proposals and report["invalidProposalRows"]:
        return 1
    return 0 if report["valid"] else 1


def estimateProposalQuality(
    *,
    rawPaths: Sequence[Path],
    labelPaths: Sequence[Path],
    resultsJson: Path,
    outDir: Path,
    minRows: int = 100,
    requiredTargets: Sequence[str] = ("filing", "news", "noAnswer", "edgar"),
) -> dict[str, Any]:
    from dartlab.providers.dart.search.goldLog import loadGoldLogRows, writeGoldLogRows
    from dartlab.providers.dart.search.qualityGate import (
        buildMissLedgerRows,
        evaluateQueryGoldRows,
        normalizeTargetKind,
        writeMissLedger,
    )

    rawRows = loadGoldLogRows(rawPaths) if rawPaths else []
    labelRows = _loadReviewRows(labelPaths)
    proxyRows, invalidRows = buildProposalProxyGoldRows(
        rawRows=rawRows,
        labelRows=labelRows,
        normalizeTarget=normalizeTargetKind,
    )
    resultsByQuery = _loadResultsByQuery(resultsJson)
    baseQuality = evaluateQueryGoldRows(
        proxyRows,
        resultsByQuery,
        minRows=minRows,
        requiredTargets=requiredTargets,
        requireRealReviewed=False,
    )
    metricEligible = bool(baseQuality.get("releaseEligible"))
    metricBlockers = list(baseQuality.get("blockers") or [])
    qualityReport = dict(baseQuality)
    qualityReport["releaseEvidence"] = False
    qualityReport["metricEligible"] = metricEligible
    qualityReport["metricBlockers"] = metricBlockers
    qualityReport["releaseEligible"] = False
    qualityReport["blockers"] = ["proposalProxyNotReleaseEvidence", *metricBlockers]
    qualityReport["nextStep"] = (
        "Use this only as a quality ceiling. Fill reviewDecision/reviewer in the decision sheet, "
        "run finalizeSearchReviewLabels.py, then run the real quality cycle for release evidence."
    )

    outDir.mkdir(parents=True, exist_ok=True)
    proxyGoldPath = outDir / "queryLogGold.proposalProxy.jsonl"
    qualityPath = outDir / "qualityCeilingReport.json"
    missLedgerPath = outDir / "missLedger.proposalProxy.jsonl"
    summaryPath = outDir / "searchProposalQualityCeiling.json"
    invalidPath = outDir / "invalidProposalRows.jsonl"
    writeGoldLogRows(proxyGoldPath, proxyRows)
    _writeJson(qualityPath, qualityReport)
    writeMissLedger(missLedgerPath, buildMissLedgerRows(proxyRows, resultsByQuery))
    _writeJsonl(invalidPath, invalidRows)

    summary = {
        "valid": not invalidRows and bool(proxyRows),
        "releaseEvidence": False,
        "invalidProposalRows": len(invalidRows),
        "proxyRows": len(proxyRows),
        "qualityReport": {
            "path": str(qualityPath),
            "metricEligible": metricEligible,
            "metrics": qualityReport.get("metrics", {}),
            "metricsByKind": qualityReport.get("metricsByKind", {}),
            "blockers": qualityReport.get("blockers", []),
        },
        "paths": {
            "proxyGold": str(proxyGoldPath),
            "qualityCeilingReport": str(qualityPath),
            "missLedger": str(missLedgerPath),
            "invalidProposalRows": str(invalidPath),
        },
    }
    _writeJson(summaryPath, summary)
    return {
        **summary,
        "qualityReport": qualityReport,
        "invalidRows": invalidRows,
    }


def buildProposalProxyGoldRows(
    *,
    rawRows: Iterable[Mapping[str, Any]],
    labelRows: Iterable[Mapping[str, Any]],
    normalizeTarget,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rawByKey = {_rowKey(row): dict(row) for row in rawRows if _rowKey(row)}
    proxyRows: list[dict[str, Any]] = []
    invalidRows: list[dict[str, Any]] = []
    for index, label in enumerate(labelRows):
        labelRow = dict(label)
        key = _rowKey(labelRow)
        raw = rawByKey.get(key, {})
        query = str(labelRow.get("query") or raw.get("query") or "").strip()
        answerable = _boolValue(labelRow.get("proposedExpectedAnswerable"))
        target = str(labelRow.get("proposedTargetKind") or labelRow.get("targetKindHint") or "").strip()
        refs = _sourceRefs(labelRow.get("proposedExpectedSourceRefs") or labelRow.get("proposedExpectedSourceRef"))
        reasons = _invalidProposalReasons(labelRow, answerable=answerable, target=target, refs=refs)
        if reasons:
            invalidRows.append(
                {
                    "rowIndex": index,
                    "queryId": key,
                    "query": query,
                    "reasons": reasons,
                }
            )
            continue

        expectedAnswerable = bool(answerable)
        targetKind = "noAnswer" if expectedAnswerable is False else normalizeTarget({"target": target})
        row: dict[str, Any] = {
            "query": query,
            "targetKind": targetKind,
            "expectedAnswerable": expectedAnswerable,
            "goldOrigin": PROXY_GOLD_ORIGIN,
            "reviewStatus": PROXY_REVIEW_STATUS,
            "labeler": PROXY_LABELER,
        }
        if key:
            row["queryId"] = key
        if expectedAnswerable:
            row["expectedSourceRef"] = refs[0]
            row["expectedSourceRefs"] = refs
        params = raw.get("params") if isinstance(raw.get("params"), Mapping) else {}
        if params:
            row["params"] = {str(k): v for k, v in params.items() if v not in (None, "")}
        proxyRows.append(row)
    return proxyRows, invalidRows


def _invalidProposalReasons(
    row: Mapping[str, Any], *, answerable: bool | None, target: str, refs: Sequence[str]
) -> list[str]:
    reasons: list[str] = []
    action = str(row.get("proposedReviewAction") or "").strip()
    if action.startswith("inspect"):
        reasons.append("proposalNeedsInspection")
    if answerable is None:
        reasons.append("missingProposedExpectedAnswerable")
    elif answerable is True:
        if not target or target == "noAnswer":
            reasons.append("answerableProposalMissingTarget")
        if not refs:
            reasons.append("answerableProposalMissingSourceRef")
    elif answerable is False and target and target != "noAnswer":
        reasons.append("noAnswerProposalTargetMismatch")
    return reasons


def _loadResultsByQuery(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(query): [dict(row) for row in rows] for query, rows in data.items()}
    if isinstance(data, list):
        out: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            if not isinstance(item, Mapping):
                continue
            query = str(item.get("query") or "")
            queryId = str(item.get("queryId") or item.get("id") or "").strip()
            rows = [dict(row) for row in item.get("results", []) if isinstance(row, Mapping)]
            if query:
                out[query] = rows
            if queryId:
                out[queryId] = rows
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _loadReviewRows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    import importlib.util

    script = Path(__file__).with_name("buildSearchReviewDecisionSheet.py")
    spec = importlib.util.spec_from_file_location("_dartlab_review_decision_sheet", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.loadReviewRows(paths)


def _rowKey(row: Mapping[str, Any]) -> str:
    return str(row.get("queryId") or row.get("id") or row.get("query") or "").strip()


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


def _writeJson(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _writeJsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(dict(row), ensure_ascii=False, sort_keys=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
