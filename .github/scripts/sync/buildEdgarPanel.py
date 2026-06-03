"""sync stage 의 EDGAR panel artifact 빌더 CLI — raw 원본 `.txt` → 16-col 보드 + 셀 (자급, offline).

gather 원본 ``data/original/edgar/docs/{cik}/{accession}.txt`` (SEC full-submission)를 자급 파싱해
``data/edgar/panel/{ticker}.parquet`` (보드) + ``data/edgar/panelCell/{ticker}.parquet`` (셀) 생산
(network 0). DART ``buildPanel.py`` 의 EDGAR analog. **원본 archive(``archiveEdgarOriginals``)가
선행돼야 한다** — 본 스크립트는 stored `.txt` 만 소비(sections 의존 0).

사용법::

    # 수집된 원본 전체 → panel (증분: 기존 보드 skip)
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
    parser = argparse.ArgumentParser(description="EDGAR panel 빌더 (raw 원본 .txt → 보드+셀 자급 파싱)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tickers", type=str, default=None, help="콤마구분 ticker (예: AAPL,MSFT)")
    group.add_argument("--all", action="store_true", help="data/original/edgar/docs/ 수집 회사 전수")
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
