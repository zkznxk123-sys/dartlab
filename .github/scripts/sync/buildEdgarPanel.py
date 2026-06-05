"""sync stage 의 EDGAR panel artifact 빌더 CLI — SEC text fetch → 16-col panel 단일 artifact.

SEC full-submission ``.txt`` 를 디스크 원본으로 저장하지 않고 메모리로 fetch 한 뒤
``data/edgar/panel/{ticker}.parquet`` 만 생산한다. DART ``buildPanel.py`` 의 EDGAR analog.

사용법::

    # listed universe 전체 → panel (증분: 기존 보드 skip)
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --all

    # 단일/여러 ticker
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --tickers AAPL,MSFT

    # 전체 재빌드 (기존 보드 덮어쓰기)
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --all --overwrite

환경변수:
    DARTLAB_DATA_DIR: 데이터 저장 경로 (기본 ./data).
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="EDGAR panel 빌더 (SEC text fetch → panel 자급 파싱)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", type=str, default=None, help="콤마구분 ticker (예: AAPL,MSFT)")
    group.add_argument("--all", action="store_true", help="listed universe 전수")
    parser.add_argument("--overwrite", action="store_true", help="기존 panel artifact 덮어쓰기 (기본 증분 skip)")
    parser.add_argument("--since-year", type=int, default=2015, help="수집 시작 연도")
    args = parser.parse_args()

    from dartlab.core.dataLoader import loadEdgarListedUniverse
    from dartlab.gather.original.edgar.collect import fetchFilingTexts
    from dartlab.gather.original.edgar.submissions import listAllFilings
    from dartlab.providers.edgar.panel.build import buildEdgarPanel

    if args.all:
        uni = loadEdgarListedUniverse(forceUpdate=True)
        tickers = [str(t).strip().upper() for t in uni["ticker"].to_list() if t]
    else:
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        print("ticker 0 — 입력 비어있음. skip.")
        return 0

    results = {}
    forms = ["10-K", "10-Q", "20-F", "40-F"]
    for ticker in tickers:
        rows = listAllFilings(ticker, sinceYear=args.since_year, forms=forms)
        grouped = fetchFilingTexts(rows)
        records = [rec for vals in grouped.values() for rec in vals]
        if len(records) < len(rows):
            print(f"[{ticker}] fetch {len(records)}/{len(rows)} — skip")
            results[ticker] = {"rows": 0, "periods": 0, "filings": 0}
            continue
        results[ticker] = buildEdgarPanel(ticker, records, overwrite=args.overwrite, verbose=True)

    built = sum(1 for r in results.values() if r["rows"] > 0)
    totalRows = sum(r["rows"] for r in results.values())
    failed = sum(1 for r in results.values() if r["rows"] == 0)
    print(f"요약: built={built} empty={failed} totalRows={totalRows:,} (ticker={len(results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
