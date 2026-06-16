"""Prepare canonical search query-log gold JSONL from raw logs and labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", default=[], help="raw query-log or gold JSON/JSONL path")
    parser.add_argument("--labels", action="append", default=[], help="reviewer label JSON/JSONL path")
    parser.add_argument("--out", required=True, help="canonical queryLogGold.real.jsonl output path")
    parser.add_argument("--summary", help="summary JSON output path")
    parser.add_argument("--label-template", help="optional reviewer label scaffold JSONL output path")
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--required-targets", default="filing,news,noAnswer,edgar")
    parser.add_argument("--default-gold-origin", default="")
    parser.add_argument("--default-review-status", default="")
    parser.add_argument("--allow-proxy-query-log", action="store_true")
    parser.add_argument("--allow-missing-source-ref", action="store_true")
    parser.add_argument("--fail-on-ineligible", action="store_true")
    args = parser.parse_args(argv)

    from dartlab.providers.dart.search.goldLog import (
        loadGoldLogRows,
        mergeGoldLogRows,
        summarizeGoldLogRows,
        writeGoldLogRows,
        writeGoldSummary,
        writeReviewerLabelTemplate,
    )

    if not args.input and not args.labels:
        raise SystemExit("--input or --labels is required")

    inputRows = loadGoldLogRows(args.input)
    labelRows = loadGoldLogRows(args.labels)
    if args.label_template:
        writeReviewerLabelTemplate(args.label_template, inputRows)
    rows = mergeGoldLogRows(
        inputRows,
        labelRows,
        defaultGoldOrigin=args.default_gold_origin,
        defaultReviewStatus=args.default_review_status,
    )
    requiredTargets = [part.strip() for part in args.required_targets.split(",") if part.strip()]
    summary = summarizeGoldLogRows(
        rows,
        minRows=args.min_rows,
        requiredTargets=requiredTargets,
        requireRealReviewed=not args.allow_proxy_query_log,
        requireSourceRef=not args.allow_missing_source_ref,
    )
    writeGoldLogRows(args.out, rows)
    if args.summary:
        writeGoldSummary(args.summary, summary)

    print(json.dumps({"releaseEligible": summary["releaseEligible"], "blockers": summary["blockers"]}))
    if args.fail_on_ineligible and not summary["releaseEligible"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
