"""sync stage 의 EDGAR panel artifact 빌더 CLI — gather sections → cross-market 16-col 미러.

이미 수집된 ``data/edgar/sections/{ticker}/`` 를 ``data/edgar/panel/{ticker}.parquet`` 로 컬럼
remap (offline — network 0). DART ``buildPanel.py`` 의 EDGAR analog. sections 수집(buildEdgarSections /
edgarSync.yml 의 docs collect)이 선행돼야 한다 (본 스크립트는 그 산출물만 소비).

사용법::

    # 수집된 sections 전체 → panel (증분: 기존 panel skip)
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --all

    # 단일/여러 ticker
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --tickers AAPL,MSFT

    # 전체 재빌드 (기존 panel 덮어쓰기)
    uv run python -X utf8 .github/scripts/sync/buildEdgarPanel.py --all --overwrite

환경변수:
    DARTLAB_DATA_DIR: 데이터 저장 경로 (기본 ./data).
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="EDGAR panel artifact 빌더 (gather sections → 16-col remap)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", type=str, default=None, help="콤마구분 ticker (예: AAPL,MSFT)")
    group.add_argument("--all", action="store_true", help="data/edgar/sections/ 수집 회사 전수")
    parser.add_argument("--overwrite", action="store_true", help="기존 panel artifact 덮어쓰기 (기본 증분 skip)")
    args = parser.parse_args()

    from dartlab.providers.edgar.panel.build import buildEdgarPanelAll

    tickers = None if args.all else [t.strip() for t in args.tickers.split(",") if t.strip()]
    if tickers is not None and not tickers:
        print("ticker 0 — 입력 비어있음. skip.")
        return 0

    # 증분 기본 — 기존 panel artifact 가 있으면 skip (overwrite 명시 시 재생성).
    results = buildEdgarPanelAll(tickers, overwrite=args.overwrite, verbose=True)

    built = sum(1 for r in results.values() if r["rows"] > 0)
    totalRows = sum(r["rows"] for r in results.values())
    failed = sum(1 for r in results.values() if r["rows"] == 0)
    print(f"요약: built={built} empty={failed} totalRows={totalRows:,} (ticker={len(results)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
