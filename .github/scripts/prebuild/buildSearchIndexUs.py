"""edgar/tickers + edgar/scan/finance → landing/static/map/search-index-us.json.

US(EDGAR) 터미널 검색 인덱스. KR ``buildSearchMain`` 의 US 대칭 — 검색→열림 성립을 위해
재무가 있는(openable) 티커만 포함한다. 행 shape = KR search-index.json 동형 +
``market='US'``::

    {"stockCode": "AAPL", "corpName": "Apple Inc.", "industry": "manufacturing",
     "market": "US", "revenue": 0.4162}

- stockCode = ticker (edgar/tickers)
- corpName  = title (회사명)
- industry  = sector (edgar scan SIC 분류), 부재 시 exchange
- revenue   = 최신 fy sales ÷1e12 (조 USD) — 검색 랭킹/표시용

별도빌드 금지 — edgar/tickers·edgar/scan 집계 SSOT 를 join 할 뿐, 엔진 회사별 재호출 없음.

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildSearchIndexUs.py [--scan PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[3]
TICKERS = ROOT / "data" / "edgar" / "tickers.parquet"
SCAN = ROOT / "data" / "edgar" / "scan" / "finance.parquet"
OUT = ROOT / "landing" / "static" / "map" / "search-index-us.json"


def build(tickersPath: Path, scanPath: Path, out: Path) -> int:
    """edgar tickers + scan finance → search-index-us.json. 반환=행 수."""
    if not tickersPath.exists() or not scanPath.exists():
        print(f"[search-us] 소스 부재 — tickers={tickersPath.exists()} scan={scanPath.exists()}", flush=True)
        return 0
    t0 = time.time()
    tk = pl.read_parquet(tickersPath, columns=["ticker", "title", "exchange"])
    scan = pl.read_parquet(scanPath)
    if "stockCode" not in scan.columns or "sales" not in scan.columns:
        print(f"[search-us] scan 스키마 부적합: {scan.columns}", flush=True)
        return 0

    # 회사별 최신 fy 1행 (sales/sector) — 다년 패널이면 latest 슬라이스, 단년이면 그대로.
    sel = (
        ["stockCode", "sales"]
        + (["sector"] if "sector" in scan.columns else [])
        + (["fy"] if "fy" in scan.columns else [])
    )
    scan = scan.select(sel)
    if "fy" in scan.columns:
        scan = scan.sort("fy", descending=True).group_by("stockCode").head(1)

    sectorMap: dict[str, str] = {}
    revMap: dict[str, float] = {}
    for r in scan.iter_rows(named=True):
        code = str(r["stockCode"]).strip().upper()
        if not code:
            continue
        if r.get("sector"):
            sectorMap[code] = str(r["sector"])
        sales = r.get("sales")
        if sales is not None:
            try:
                revMap[code] = round(float(sales) / 1_000_000_000_000, 4)
            except (ValueError, TypeError):
                pass

    rows: list[dict] = []
    for r in tk.iter_rows(named=True):
        ticker = str(r["ticker"]).strip().upper()
        if not ticker or ticker not in revMap:  # 재무 없는 티커 제외 (검색돼도 못 여니까)
            continue
        rows.append(
            {
                "stockCode": ticker,
                "corpName": str(r["title"]).strip() if r["title"] else ticker,
                "industry": sectorMap.get(ticker) or (str(r["exchange"]).strip() if r["exchange"] else "US"),
                "market": "US",
                "revenue": revMap[ticker],
            }
        )
    # 매출 내림차순 (검색 랭킹 대형주 우선)
    rows.sort(key=lambda x: x["revenue"], reverse=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sizeKb = out.stat().st_size / 1024
    print(f"[search-us] 완료: {len(rows)}종목, {sizeKb:.1f}KB, {time.time() - t0:.0f}초 → {out}", flush=True)
    return len(rows)


def main() -> int:
    """CLI 진입 — edgar tickers + scan → search-index-us.json."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tickers", default=str(TICKERS))
    parser.add_argument("--scan", default=str(SCAN))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    n = build(Path(args.tickers), Path(args.scan), Path(args.out))
    return 0 if n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
