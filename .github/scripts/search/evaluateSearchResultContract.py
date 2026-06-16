"""Audit product search result rows for sourceRef/dataAsOf/evidence contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-json", help="precomputed result rows JSON/JSONL path")
    parser.add_argument("--query", action="append", default=[], help="query to run through dartlab.search")
    parser.add_argument("--queries-json", help="JSON/JSONL query list path")
    parser.add_argument("--out", required=True, help="contract report JSON path")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--scope", default="auto")
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--allow-missing-data-as-of", action="store_true")
    parser.add_argument("--allow-missing-snippet", action="store_true")
    parser.add_argument("--allow-missing-card-evidence", action="store_true")
    parser.add_argument("--fail-on-error", action="store_true")
    args = parser.parse_args(argv)

    from dartlab.providers.dart.search.resultContract import (
        auditSearchResultRows,
        flattenResultRows,
        loadResultRows,
        writeResultContractReport,
    )

    if args.results_json:
        rows = loadResultRows(args.results_json)
    else:
        queries = list(args.query)
        if args.queries_json:
            queries.extend(_loadQueries(args.queries_json))
        if not queries:
            raise SystemExit("--results-json, --query, or --queries-json is required")
        rows = flattenResultRows(_runSearch(queries, limit=args.limit, scope=args.scope))

    report = auditSearchResultRows(
        rows,
        minRows=args.min_rows,
        requireDataAsOf=not args.allow_missing_data_as_of,
        requireSnippet=not args.allow_missing_snippet,
        requireCardEvidence=not args.allow_missing_card_evidence,
    )
    writeResultContractReport(args.out, report)
    print(json.dumps({"valid": report["valid"], "blockers": report["blockers"]}, ensure_ascii=False))
    if args.fail_on_error and not report["valid"]:
        return 1
    return 0


def _loadQueries(path: str) -> list[str]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".jsonl":
        return [
            str(json.loads(line).get("query") if line.strip().startswith("{") else line).strip()
            for line in text.splitlines()
            if line.strip()
        ]
    data = json.loads(text) if text.strip() else []
    if isinstance(data, list):
        return [
            str(item.get("query") if isinstance(item, dict) else item).strip() for item in data if str(item).strip()
        ]
    if isinstance(data, dict):
        rows = data.get("queries") or data.get("rows")
        if isinstance(rows, list):
            return [
                str(item.get("query") if isinstance(item, dict) else item).strip() for item in rows if str(item).strip()
            ]
    raise ValueError(f"unsupported queries-json shape: {path}")


def _runSearch(queries: list[str], *, limit: int, scope: str) -> list[dict[str, Any]]:
    from dartlab.providers.dart.search.api import search

    out = []
    for query in queries:
        df = search(query, limit=limit, scope=scope)
        out.append({"query": query, "results": df.to_dicts()})
    return out


if __name__ == "__main__":
    sys.exit(main())
