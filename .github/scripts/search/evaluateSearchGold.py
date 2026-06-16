"""Evaluate product search against real query-log gold."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, help="JSON/JSONL query-log gold path")
    parser.add_argument("--out", required=True, help="quality report JSON path")
    parser.add_argument("--miss-ledger", help="miss ledger JSONL path")
    parser.add_argument("--results-json", help="precomputed results by query JSON path")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--min-rows", type=int, default=100)
    parser.add_argument("--required-targets", default="filing,news,noAnswer")
    parser.add_argument("--allow-proxy-query-log", action="store_true")
    parser.add_argument("--fail-on-ineligible", action="store_true")
    args = parser.parse_args(argv)

    from dartlab.providers.dart.search.qualityGate import (
        buildMissLedgerRows,
        evaluateQueryGoldRows,
        loadQueryGold,
        writeMissLedger,
    )

    goldRows = loadQueryGold(args.gold)
    resultsByQuery = _loadResultsByQuery(args.results_json)
    if resultsByQuery is None:
        resultsByQuery = _runSearch(goldRows, limit=args.limit, scope=args.scope)

    requiredTargets = [part.strip() for part in args.required_targets.split(",") if part.strip()]
    report = evaluateQueryGoldRows(
        goldRows,
        resultsByQuery,
        minRows=args.min_rows,
        requiredTargets=requiredTargets,
        requireRealReviewed=not args.allow_proxy_query_log,
    )
    outPath = Path(args.out)
    outPath.parent.mkdir(parents=True, exist_ok=True)
    outPath.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    if args.miss_ledger:
        writeMissLedger(args.miss_ledger, buildMissLedgerRows(goldRows, resultsByQuery))

    print(
        json.dumps({"releaseEligible": report["releaseEligible"], "blockers": report["blockers"]}, ensure_ascii=False)
    )
    if args.fail_on_ineligible and not report["releaseEligible"]:
        return 1
    return 0


def _loadResultsByQuery(path: str | None) -> dict[str, list[dict[str, Any]]] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return {str(query): [dict(row) for row in rows] for query, rows in data.items()}
    if isinstance(data, list):
        out: dict[str, list[dict[str, Any]]] = {}
        for item in data:
            if isinstance(item, dict):
                out[str(item.get("query") or "")] = [dict(row) for row in item.get("results", [])]
        return out
    raise ValueError(f"unsupported results-json shape: {path}")


def _runSearch(goldRows: list[dict[str, Any]], *, limit: int, scope: str) -> dict[str, list[dict[str, Any]]]:
    from dartlab.providers.dart.search.api import search

    out: dict[str, list[dict[str, Any]]] = {}
    for row in goldRows:
        query = str(row.get("query") or "")
        if query in out:
            continue
        out[query] = search(query, limit=limit, scope=scope).to_dicts()
    return out


if __name__ == "__main__":
    sys.exit(main())
