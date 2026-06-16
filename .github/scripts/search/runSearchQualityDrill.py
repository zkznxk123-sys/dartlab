"""Run a non-release drill for query-log gold and miss-ledger tooling."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="quality drill report JSON path")
    parser.add_argument("--canonical-gold", help="optional canonical gold JSONL output path")
    parser.add_argument("--label-template", help="optional reviewer label template JSONL output path")
    parser.add_argument("--miss-ledger", help="optional miss ledger JSONL output path")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    report = runQualityDrill(
        canonicalGoldPath=Path(args.canonical_gold) if args.canonical_gold else None,
        labelTemplatePath=Path(args.label_template) if args.label_template else None,
        missLedgerPath=Path(args.miss_ledger) if args.miss_ledger else None,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"valid": report["valid"], "blockers": report["blockers"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    return 0


def runQualityDrill(
    *,
    canonicalGoldPath: Path | None = None,
    labelTemplatePath: Path | None = None,
    missLedgerPath: Path | None = None,
) -> dict[str, Any]:
    from dartlab.providers.dart.search.goldLog import (
        buildReviewerLabelTemplateRows,
        mergeGoldLogRows,
        summarizeGoldLogRows,
        writeGoldLogRows,
    )
    from dartlab.providers.dart.search.qualityGate import (
        buildMissLedgerRows,
        evaluateQueryGoldRows,
        writeMissLedger,
    )

    rawRows = _rawRows()
    labels = _reviewedLabels()
    canonical = mergeGoldLogRows(rawRows, labels)
    summary = summarizeGoldLogRows(
        canonical,
        minRows=4,
        requiredTargets=["filing", "news", "noAnswer", "edgar"],
        requireRealReviewed=False,
        requireSourceRef=True,
    )
    if canonicalGoldPath is not None:
        writeGoldLogRows(canonicalGoldPath, canonical)
    if labelTemplatePath is not None:
        writeGoldLogRows(labelTemplatePath, buildReviewerLabelTemplateRows(rawRows))

    resultsByQuery = _resultsByQuery()
    quality = evaluateQueryGoldRows(
        canonical,
        resultsByQuery,
        minRows=4,
        requiredTargets=["filing", "news", "noAnswer", "edgar"],
        requireRealReviewed=False,
    )
    missRows = buildMissLedgerRows(canonical, resultsByQuery)
    if missLedgerPath is not None:
        writeMissLedger(missLedgerPath, missRows)

    blockers = [*summary["blockers"], *quality["blockers"]]
    return {
        "valid": not blockers,
        "blockers": blockers,
        "releaseEvidence": False,
        "drill": "query-log-gold-toolchain",
        "summary": summary,
        "quality": quality,
        "missLedgerRows": len(missRows),
    }


def _rawRows() -> list[dict[str, Any]]:
    return [
        {
            "queryId": "drill-filing",
            "query": "유상증자 공시 원문",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "candidate",
            "topSourceRefs": ["dart:allFilings:1"],
        },
        {
            "queryId": "drill-news",
            "query": "공시 말고 뉴스로 환율 기사",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "candidate",
            "topSourceRefs": ["news:1"],
        },
        {
            "queryId": "drill-edgar",
            "query": "EDGAR 10-K revenue recognition",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "candidate",
            "topSourceRefs": ["edgar:1"],
        },
        {
            "queryId": "drill-no-answer",
            "query": "없는회사 2099년 합병 공시",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "candidate",
            "topSourceRefs": [],
        },
    ]


def _reviewedLabels() -> list[dict[str, Any]]:
    return [
        {
            "queryId": "drill-filing",
            "query": "유상증자 공시 원문",
            "targetKind": "filing",
            "expectedSourceRef": "dart:allFilings:1",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "drillReviewed",
        },
        {
            "queryId": "drill-news",
            "query": "공시 말고 뉴스로 환율 기사",
            "targetKind": "news",
            "expectedSourceRef": "news:1",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "drillReviewed",
        },
        {
            "queryId": "drill-edgar",
            "query": "EDGAR 10-K revenue recognition",
            "targetKind": "edgar",
            "expectedSourceRef": "edgar:1",
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "drillReviewed",
        },
        {
            "queryId": "drill-no-answer",
            "query": "없는회사 2099년 합병 공시",
            "targetKind": "noAnswer",
            "expectedAnswerable": False,
            "goldOrigin": "drillSynthetic",
            "reviewStatus": "drillReviewed",
        },
    ]


def _resultsByQuery() -> dict[str, list[dict[str, Any]]]:
    return {
        "유상증자 공시 원문": [
            {
                "source": "allFilings",
                "sourceRef": "dart:allFilings:1",
                "answerable": True,
                "dataAsOf": "20260616",
            }
        ],
        "공시 말고 뉴스로 환율 기사": [
            {
                "source": "news",
                "sourceRef": "news:1",
                "answerable": True,
                "dataAsOf": "20260616",
            }
        ],
        "EDGAR 10-K revenue recognition": [
            {
                "source": "edgar-panel",
                "sourceRef": "edgar:1",
                "answerable": True,
                "dataAsOf": "20260616",
            }
        ],
        "없는회사 2099년 합병 공시": [
            {
                "source": "allFilings",
                "sourceRef": "dart:allFilings:other",
                "answerable": False,
                "notAnswerableReason": "facetMismatch:company",
                "dataAsOf": "20260616",
            }
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
