"""EDGAR panel build CLI — ``python -X utf8 -m dartlab.providers.edgar.panel.build``.

raw 원본 ``data/original/edgar/docs/{cik}/*.txt`` 자급 XBRL 파싱 → 보드 + 셀 (offline, network 0).

사용::

    python -X utf8 -m dartlab.providers.edgar.panel.build --tickers AAPL,MSFT
    python -X utf8 -m dartlab.providers.edgar.panel.build --all                # 수집된 원본 전수
    python -X utf8 -m dartlab.providers.edgar.panel.build --all --no-overwrite  # 증분(기존 보드 skip)
"""

from __future__ import annotations

import argparse

from .builder import buildEdgarPanelAll


def _main() -> None:
    """argparse → buildEdgarPanelAll 위임 + 결과 요약 출력."""
    parser = argparse.ArgumentParser(prog="dartlab.providers.edgar.panel.build")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", help="콤마구분 ticker 목록 (예: AAPL,MSFT)")
    group.add_argument("--all", action="store_true", help="data/original/edgar/docs/ 수집 회사 전수")
    parser.add_argument("--no-overwrite", action="store_true", help="기존 보드 artifact skip(증분)")
    parser.add_argument("--quiet", action="store_true", help="per-ticker 로그 억제")
    args = parser.parse_args()

    tickers = None if args.all else [t.strip() for t in args.tickers.split(",") if t.strip()]
    results = buildEdgarPanelAll(tickers, overwrite=not args.no_overwrite, verbose=not args.quiet)

    totalRows = sum(r["rows"] for r in results.values())
    totalCells = sum(r.get("cells", 0) for r in results.values())
    built = sum(1 for r in results.values() if r["rows"] > 0)
    print(f"edgar panel build: {built}/{len(results)} ticker, {totalRows:,} board rows, {totalCells:,} cells")  # noqa: T201


if __name__ == "__main__":
    _main()
