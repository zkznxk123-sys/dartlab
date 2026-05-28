"""sync stage 의 EDGAR sections artifact 빌더 CLI — plan delegated-prancing-tower PR-E2.

EDGAR ticker universe 를 받아 ``data/edgar/sections/{ticker}/{period}.parquet`` 영속화.
dual-write 강행 — fetchEdgarDocs 가 옛 docs.parquet + 신 sections artifact 동시 emit.

사용법::

    # 단일 ticker
    uv run python -X utf8 .github/scripts/sync/buildEdgarSections.py --ticker AAPL

    # SP500 incremental (기존 parquet 있는 ticker skip)
    uv run python -X utf8 .github/scripts/sync/buildEdgarSections.py --tier sp500 --mode incremental

    # 전체 universe full rebuild (~수 시간)
    uv run python -X utf8 .github/scripts/sync/buildEdgarSections.py --tier all --mode full --limit 100

환경변수:
    DARTLAB_DATA_DIR: 데이터 저장 경로 (기본 ./data).
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable


def _resolveTickers(tier: str, limit: int | None) -> list[str]:
    """tier → ticker list 해석.

    Args:
        tier: ``"sp500"`` / ``"nasdaq100"`` / ``"russell1000"`` / ``"all"`` 또는 단일 ticker.
        limit: 최대 ticker 수.

    Returns:
        ticker list.

    Raises:
        없음.

    Example:
        >>> _resolveTickers("sp500", 10)  # doctest: +SKIP
    """
    if tier in ("sp500", "nasdaq", "nasdaq100", "russell1000", "all"):
        from dartlab.core.dataLoader import loadEdgarTargetUniverse

        universe = loadEdgarTargetUniverse(tier)
        tickers = universe["ticker"].to_list() if universe is not None else []
    else:
        tickers = [tier]
    if limit:
        tickers = tickers[:limit]
    return tickers


def _runBatch(
    tickers: Iterable[str],
    *,
    sinceYear: int,
    incremental: bool,
    cooldownSeconds: float,
    batchSize: int,
) -> dict:
    """ticker batch 빌드 — 옛 fetchEdgarDocs 호출이 dual-write (docs + sections).

    incremental=True 면 기존 ``data/edgar/docs/{ticker}.parquet`` + ``data/edgar/sections/{ticker}/``
    의 accession_no diff 검사 후 missing 만 fetch. PR-E2 1 차 구현은 ticker-level skip
    (둘 다 존재하면 skip). PR-E3 가 accession-level diff 추가.

    Args:
        tickers: ticker iterable.
        sinceYear: 수집 시작 연도.
        incremental: 기존 artifact 있으면 skip 여부.
        cooldownSeconds: batch 사이 sleep.
        batchSize: cooldown 단위.

    Returns:
        ``{"processed": N, "skipped": M, "failed": K, "totalPeriods": P, "totalRows": R}``.
    """
    from dartlab.core.dataLoader import _getDataRoot
    from dartlab.providers.edgar.docs.fetch import fetchEdgarDocs
    from dartlab.providers.edgar.docs.sections.sectionsStorage import (
        hasSectionsArtifact,
    )

    docsDir = _getDataRoot() / "edgar" / "docs"
    docsDir.mkdir(parents=True, exist_ok=True)
    processed = skipped = failed = totalPeriods = totalRows = 0

    tickerList = list(tickers)
    for idx, ticker in enumerate(tickerList, start=1):
        ticker = ticker.upper()
        docsPath = docsDir / f"{ticker}.parquet"
        if incremental and docsPath.exists() and hasSectionsArtifact(ticker):
            skipped += 1
            print(f"[{idx}/{len(tickerList)}] {ticker} SKIP (artifact 존재)")
            continue
        try:
            fetchEdgarDocs(ticker, docsPath, sinceYear=sinceYear, showProgress=False)
            # fetchEdgarDocs 의 dual-write 가 sections artifact 도 emit 했는지 확인.
            from dartlab.providers.edgar.docs.sections.sectionsStorage import (
                listAvailablePeriods,
            )

            periods = listAvailablePeriods(ticker)
            totalPeriods += len(periods)
            processed += 1
            print(f"[{idx}/{len(tickerList)}] {ticker} OK (periods={len(periods)})")
        except (OSError, ValueError) as exc:
            failed += 1
            print(f"[{idx}/{len(tickerList)}] {ticker} FAIL: {exc}")
        if batchSize > 0 and idx < len(tickerList) and idx % batchSize == 0:
            time.sleep(cooldownSeconds)

    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "totalPeriods": totalPeriods,
        "totalRows": totalRows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="EDGAR sections artifact 증분 빌더 (dual-write)")
    parser.add_argument("--ticker", type=str, default=None, help="단일 ticker")
    parser.add_argument(
        "--tier",
        type=str,
        default="sp500",
        help="universe tier (sp500/nasdaq100/russell1000/all) 또는 ticker",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="incremental",
        choices=["incremental", "full"],
        help="incremental: 기존 artifact 있으면 skip. full: 전체 재빌드.",
    )
    parser.add_argument("--limit", type=int, default=None, help="최대 ticker 수")
    parser.add_argument("--sinceYear", type=int, default=2009, help="수집 시작 연도")
    parser.add_argument("--cooldown", type=float, default=8.0, help="batch 사이 sleep (sec)")
    parser.add_argument("--batchSize", type=int, default=25, help="cooldown 단위")
    args = parser.parse_args()

    if args.ticker:
        tickers = [args.ticker]
    else:
        tickers = _resolveTickers(args.tier, args.limit)

    if not tickers:
        print("ticker 0 — universe 비어있거나 tier 미인식. skip.")
        return 0

    incremental = args.mode == "incremental"
    print(f"빌드 시작: ticker={len(tickers)} mode={args.mode} sinceYear={args.sinceYear}")
    result = _runBatch(
        tickers,
        sinceYear=args.sinceYear,
        incremental=incremental,
        cooldownSeconds=args.cooldown,
        batchSize=args.batchSize,
    )
    print("요약: processed={processed} skipped={skipped} failed={failed} totalPeriods={totalPeriods}".format(**result))
    return 0 if result["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
