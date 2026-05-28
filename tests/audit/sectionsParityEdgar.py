"""EDGAR sections artifact parity 측정 — PR-E7 안전 게이트 SSOT.

옛 ``data/edgar/docs/{ticker}.parquet`` (long: section_title/section_content) 와 신
``data/edgar/sections/{ticker}/{period}.parquet`` (long: topic/content_plain) 의
schema parity 측정. 운영자가 *4 주 연속 0 violations* 확인 후 PR-E7b (docs.parquet
폐기) 진행.

usage:
    uv run python -X utf8 tests/audit/sectionsParityEdgar.py --tickers AAPL,MSFT,GOOGL,AMZN,NVDA
    uv run python -X utf8 tests/audit/sectionsParityEdgar.py --strict --json out.json
    uv run python -X utf8 tests/audit/sectionsParityEdgar.py --tier sp500 --limit 100

종료 코드:
    0 — 모든 ticker parity 0 violations (게이트 통과).
    1 — 1 개 이상 violations (게이트 미통과).
    2 — artifact 부재 ticker 1 개 이상 (측정 불가 — 게이트 reset).

측정 메트릭:
    - filing coverage — 옛 docs.parquet 의 accession_no set ⊆ 신 _index.parquet accession_no set
    - topic coverage — 옛 section_title 매핑 set vs 신 topic set (mapper.mapSectionTitle 동치성)
    - row count — 옛 vs 신 의 period 별 section row 수 (분기 ±5% 이내)

violations 출력 예:
    AAPL: [{kind: "missing_accession", value: "0000320193-24-000123"}, ...]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import polars as pl

from dartlab.providers.edgar.docs.sections.mapper import mapSectionTitle
from dartlab.providers.edgar.docs.sections.sectionsStorage import (
    hasSectionsArtifact,
    loadSectionsIndex,
    loadSectionsLong,
)

_log = logging.getLogger(__name__)


# PR-E7 안전 게이트 baseline.
DEFAULT_TICKERS = ("AAPL", "MSFT", "GOOGL", "AMZN", "NVDA")


def measureTicker(ticker: str) -> dict:
    """1 ticker 의 옛/신 parity 측정.

    Args:
        ticker: US ticker (대소문자 무관).

    Returns:
        ``{
            "ticker": str,
            "status": "ok" | "missing_old" | "missing_new" | "violations",
            "oldAccessionCount": int,
            "newAccessionCount": int,
            "missingAccessions": list[str],
            "topicMismatchCount": int,
            "rowCountDeltaPct": float,
        }``.

    Raises:
        없음.
    """
    tickerUpper = ticker.upper()
    from dartlab.core.dataLoader import _getDataRoot

    docsPath = _getDataRoot() / "edgar" / "docs" / f"{tickerUpper}.parquet"
    if not docsPath.exists():
        return {"ticker": tickerUpper, "status": "missing_old", "reason": "data/edgar/docs/{ticker}.parquet 부재"}
    if not hasSectionsArtifact(tickerUpper):
        return {
            "ticker": tickerUpper,
            "status": "missing_new",
            "reason": "sections artifact 부재 — buildEdgarSections 실행 필요",
        }

    # 옛 path — docs.parquet.
    try:
        oldDf = pl.read_parquet(str(docsPath))
    except (OSError, pl.exceptions.ComputeError) as exc:
        return {"ticker": tickerUpper, "status": "missing_old", "reason": str(exc)}

    # 신 path — sections artifact + _index.parquet.
    newIndex = loadSectionsIndex(tickerUpper)
    if newIndex is None or newIndex.is_empty():
        return {"ticker": tickerUpper, "status": "missing_new", "reason": "_index.parquet 부재 또는 빈 결과"}

    oldAccessions = (
        set(oldDf["accession_no"].drop_nulls().unique().to_list()) if "accession_no" in oldDf.columns else set()
    )
    newAccessions = set(newIndex["accession_no"].drop_nulls().unique().to_list())

    missingAccessions = sorted(oldAccessions - newAccessions)

    # topic parity — 옛 section_title 의 mapSectionTitle 결과 vs 신 topic.
    oldTopics = set()
    if "section_title" in oldDf.columns and "form_type" in oldDf.columns:
        for row in oldDf.select("form_type", "section_title").iter_rows():
            formType, title = row
            if formType and title:
                oldTopics.add(mapSectionTitle(str(formType), str(title)))

    newLong = loadSectionsLong(tickerUpper, columns=["topic"])
    newTopics = set(newLong["topic"].drop_nulls().unique().to_list()) if newLong is not None else set()

    topicMismatch = sorted(oldTopics - newTopics)

    oldRowCount = oldDf.height
    newRowCount = sum(
        int(p)
        for p in [
            pl.scan_parquet([str(_getDataRoot() / "edgar" / "sections" / tickerUpper / f"{period}.parquet")])
            .select(pl.len())
            .collect()
            .item()
            for period in [
                p.stem
                for p in (_getDataRoot() / "edgar" / "sections" / tickerUpper).glob("*.parquet")
                if not p.stem.startswith("_")
            ]
        ]
    )
    rowCountDeltaPct = ((newRowCount - oldRowCount) / max(oldRowCount, 1)) * 100.0

    violations = []
    if missingAccessions:
        violations.append(
            {"kind": "missing_accession", "count": len(missingAccessions), "sample": missingAccessions[:5]}
        )
    if topicMismatch:
        violations.append({"kind": "topic_mismatch", "count": len(topicMismatch), "sample": topicMismatch[:5]})

    return {
        "ticker": tickerUpper,
        "status": "ok" if not violations else "violations",
        "oldAccessionCount": len(oldAccessions),
        "newAccessionCount": len(newAccessions),
        "missingAccessions": missingAccessions[:20],
        "oldTopicCount": len(oldTopics),
        "newTopicCount": len(newTopics),
        "topicMismatchCount": len(topicMismatch),
        "topicMismatchSample": topicMismatch[:5],
        "oldRowCount": oldRowCount,
        "newRowCount": newRowCount,
        "rowCountDeltaPct": round(rowCountDeltaPct, 2),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="EDGAR sections parity 측정 (PR-E7 안전 게이트)")
    parser.add_argument("--tickers", type=str, default=None, help="comma-separated ticker list")
    parser.add_argument("--tier", type=str, default=None, help="universe tier (sp500/...)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--strict", action="store_true", help="violations 1 개라도 있으면 exit 1")
    parser.add_argument("--json", type=str, default=None, help="결과 JSON 파일 출력 경로")
    args = parser.parse_args()

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    elif args.tier:
        from dartlab.core.dataLoader import loadEdgarTargetUniverse

        universe = loadEdgarTargetUniverse(args.tier)
        tickers = universe["ticker"].to_list() if universe is not None else []
        if args.limit:
            tickers = tickers[: args.limit]
    else:
        tickers = list(DEFAULT_TICKERS)

    results = [measureTicker(t) for t in tickers]
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"결과 JSON: {args.json}")

    totalViolations = sum(len(r.get("violations", [])) for r in results)
    missingOld = sum(1 for r in results if r["status"] == "missing_old")
    missingNew = sum(1 for r in results if r["status"] == "missing_new")

    print(f"\n=== EDGAR sections parity ({len(results)} ticker) ===")
    for r in results:
        print(
            f"  {r['ticker']:<6} {r['status']:<14} "
            f"acc {r.get('oldAccessionCount', '-')}→{r.get('newAccessionCount', '-')} "
            f"topics {r.get('oldTopicCount', '-')}→{r.get('newTopicCount', '-')} "
            f"rowsΔ {r.get('rowCountDeltaPct', '-')}%"
        )
    print(f"\nsummary: violations={totalViolations} missing_old={missingOld} missing_new={missingNew}")

    if missingOld + missingNew > 0:
        return 2
    if args.strict and totalViolations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
