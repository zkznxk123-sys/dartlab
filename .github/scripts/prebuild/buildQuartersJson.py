"""finance.parquet → landing/static/dashboards/quarters.json

대시보드 v19 신규 Tier — 전 상장사 × 20분기 주요 계정 시계열.

- IS/CF: YTD(누적) 공시값 → 분기별 파생 (Q2=H1-Q1, Q3=9M-H1, Q4=FY-9M)
- BS: 기말 point-in-time 그대로

출력 shape::

    {
      "version": "v19",
      "periods": ["21Q1", "21Q2", ..., "25Q4"],  // 20개
      "companies": {
        "005930": {
          "is": { "sales": [...20], "op": [...20], "net": [...20] },
          "cf": { "ocf": [...20] },
          "bs": { "totalAsset": [...20], "totalLiab": [...20], "totalEquity": [...20], "cash": [...20] }
        },
        ...
      }
    }

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildQuartersJson.py
    # ~3분, <2GB
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "dart" / "scan" / "finance.parquet"
OUT = ROOT / "landing" / "static" / "dashboards" / "quarters.json"

# 5년 × 4 분기 = 20분기
YEARS = ["2021", "2022", "2023", "2024", "2025"]

# reprt_code → 분기 인덱스 (cumulative 정의)
# 11013 = Q1 (1-3월)          → Q1 YTD
# 11012 = 반기 (1-6월)        → Q2 YTD (H1)
# 11014 = 3분기 (1-9월)       → Q3 YTD (9M)
# 11011 = 사업보고서 (1-12월) → Q4 YTD (FY)

IS_ACCOUNTS = {
    "sales": "sales",
    "op": "operating_profit",
    "net": "net_profit",
}
CF_ACCOUNTS = {
    "ocf": "operating_cashflow",
    "icf": "investing_cashflow",
}
BS_ACCOUNTS = {
    "totalAsset": "total_assets",
    "totalLiab": "total_liabilities",
    "totalEquity": "total_stockholders_equity",
    "cash": "cash_and_cash_equivalents",
}


def _periods() -> list[str]:
    out = []
    for y in YEARS:
        for q in range(1, 5):
            out.append(f"{y[-2:]}Q{q}")
    return out


def _to_trillion(v: str | None) -> float | None:
    if v is None or v == "" or v == "-":
        return None
    try:
        x = int(v.replace(",", "").strip())
        return round(x / 1_000_000_000_000, 2)
    except (ValueError, AttributeError):
        return None


def _extract_ytd(df: pl.DataFrame, sj_div: str, account_id: str) -> dict[tuple[str, str], float | None]:
    """(year, reprt_code) → value (조원).

    연결(CFS) 우선, 없으면 별도(OFS).
    """
    rows = df.filter((pl.col("sj_div") == sj_div) & (pl.col("account_id_std") == account_id))
    if rows.is_empty():
        return {}
    # CFS 우선
    cfs = rows.filter(pl.col("fs_div") == "CFS")
    use = cfs if not cfs.is_empty() else rows
    out: dict[tuple[str, str], float | None] = {}
    for row in use.iter_rows(named=True):
        key = (row["bsns_year"], row["reprt_code"])
        if key not in out:
            out[key] = _to_trillion(row["thstrm_amount"])
    return out


def _derive_quarters_is_cf(vals: dict[tuple[str, str], float | None]) -> list[float | None]:
    """DART scan 의 IS/CF `thstrm_amount` 는 **각 분기 standalone** 값.

    - Q1 = 11013 (1분기)
    - Q2 = 11012 (반기 — 실제 Q2 standalone 값)
    - Q3 = 11014 (3분기 — Q3 standalone)
    - Q4 = 11011 - (Q1+Q2+Q3)  [사업보고서 annual 에서 3분기 빼기]
    """
    result: list[float | None] = []
    for y in YEARS:
        q1 = vals.get((y, "11013"))
        q2 = vals.get((y, "11012"))
        q3 = vals.get((y, "11014"))
        fy = vals.get((y, "11011"))

        result.append(q1)
        result.append(q2)
        result.append(q3)

        # Q4 = FY - (Q1+Q2+Q3). 셋 중 하나라도 None 이면 Q4 도 None.
        if all(v is not None for v in (fy, q1, q2, q3)):
            q4 = fy - q1 - q2 - q3
            # 극단 이상치 (음수 큰 값) 는 기각
            if q4 < 0 and abs(q4) > abs(fy) * 0.5:
                result.append(None)
            else:
                result.append(round(q4, 2))
        else:
            result.append(None)
    return result


def _extract_bs_point_in_time(
    ytd: dict[tuple[str, str], float | None],
) -> list[float | None]:
    """BS — 각 분기말 기준 그대로 (누적 아님). 20개."""
    result: list[float | None] = []
    for y in YEARS:
        # 각 분기는 해당 reprt_code 말의 BS 값
        result.append(ytd.get((y, "11013")))  # Q1
        result.append(ytd.get((y, "11012")))  # Q2 (H1 말)
        result.append(ytd.get((y, "11014")))  # Q3 (9M 말)
        result.append(ytd.get((y, "11011")))  # Q4 (FY 말)
    return result


def _extract_company(df: pl.DataFrame, stockCode: str) -> dict | None:
    c_df = df.filter(pl.col("stockCode") == stockCode)
    if c_df.is_empty():
        return None

    is_out: dict[str, list[float | None]] = {}
    for key, acc_id in IS_ACCOUNTS.items():
        ytd = _extract_ytd(c_df, "IS", acc_id)
        if ytd:
            is_out[key] = _derive_quarters_is_cf(ytd)

    cf_out: dict[str, list[float | None]] = {}
    for key, acc_id in CF_ACCOUNTS.items():
        ytd = _extract_ytd(c_df, "CF", acc_id)
        if ytd:
            cf_out[key] = _derive_quarters_is_cf(ytd)

    bs_out: dict[str, list[float | None]] = {}
    for key, acc_id in BS_ACCOUNTS.items():
        ytd = _extract_ytd(c_df, "BS", acc_id)
        if ytd:
            bs_out[key] = _extract_bs_point_in_time(ytd)

    if not is_out and not cf_out and not bs_out:
        return None

    return {"is": is_out, "cf": cf_out, "bs": bs_out}


def main() -> int:
    print(f"[quarters.json 빌드] {SRC}...", flush=True)
    t0 = time.time()

    df = pl.read_parquet(SRC)
    print(f"  shape: {df.shape}, loaded in {time.time() - t0:.1f}s", flush=True)

    df = df.filter(pl.col("stockCode").str.len_chars() == 6)
    df = df.select(["stockCode", "bsns_year", "reprt_code", "sj_div", "account_id_std", "fs_div", "thstrm_amount"])
    df = df.unique(
        subset=["stockCode", "bsns_year", "reprt_code", "sj_div", "account_id_std", "fs_div"],
        keep="first",
    )
    print(f"  filtered: {df.shape}", flush=True)

    stockCodes = sorted(df["stockCode"].unique().to_list())
    print(f"  companies: {len(stockCodes)}", flush=True)

    companies: dict[str, dict] = {}
    t1 = time.time()
    for i, code in enumerate(stockCodes, 1):
        data = _extract_company(df, code)
        if data:
            companies[code] = data
        if i % 500 == 0:
            rate = i / (time.time() - t1)
            print(f"  [{i}/{len(stockCodes)}] {rate:.0f}/s", flush=True)

    periods = _periods()
    output = {"version": "v19", "periods": periods, "companies": companies}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")

    size_mb = OUT.stat().st_size / 1024 / 1024
    elapsed = time.time() - t0
    print(f"완료: {len(companies)}사, {size_mb:.1f}MB, {elapsed:.0f}초 → {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
