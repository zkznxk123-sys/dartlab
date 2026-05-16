"""finance.parquet → landing/static/dashboards/finance.json (전 상장사 경량 5Y).

대시보드 v16 Tier 1 — 모든 회사의 IS/BS/CF 를 단일 JSON 으로.
Company 객체 안 만듬 → Polars lazy 로 직접 변환 → OOM 없음.

출력 shape::

    {
      "version": "v16",
      "years": ["2021", ..., "2025"],
      "companies": {
        "005930": {
          "is":  { "sales": [...5], "op": [...5], "net": [...5], "opMargin": [...5] },
          "bs":  { "assets": {...6×5}, "liab": {...6×5}, "equity": {...5×5} },
          "cf":  { "opening", "op", "inv", "fin", "fx", "closing" },
          "ratios": { "roe": [...5], "debtRatio": [...5] }
        },
        ...
      }
    }

실행::

    uv run python -X utf8 .github/scripts/prebuild/buildFinanceJson.py
    # ~5분, <2GB 메모리
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "dart" / "scan" / "finance.parquet"
OUT = ROOT / "landing" / "static" / "dashboards" / "finance.json"

# 5년 범위
YEARS = ["2021", "2022", "2023", "2024", "2025"]

# account_id_std → 출력 필드 매핑
IS_MAP = {
    "sales": "sales",
    "operating_profit": "op",
    "net_profit": "net",
}

BS_ASSETS = {
    "cash_and_cash_equivalents": "cash",
    "trade_and_other_receivables": "recv",
    "inventories": "inv",
    "tangible_assets": "tang",
    "intangible_assets": "intan",
}

BS_LIAB = {
    "trade_and_other_payables": "pay",
    "shortterm_borrowings": "shortDebt",
    "longterm_borrowings": "longDebt",
    "debentures": "bonds",
    "provisions": "prov",
}

BS_EQUITY = {
    "paidin_capital": "paidIn",
    "share_premium": "surplus",
    "retained_earnings": "retained",
    "other_reserves": "otherComp",
}

BS_TOTALS = {
    "total_assets": "totalAsset",
    "total_liabilities": "totalLiab",
    "total_stockholders_equity": "totalEquity",
    "current_assets": "currAsset",
    "current_liabilities": "currLiab",
}

CF_MAP = {
    "operating_cashflow": "op",
    "investing_cashflow": "inv",
    "cash_flows_from_financing_activities": "fin",
    "cash_and_cash_equivalents_beginning": "opening",
    "cash_and_cash_equivalents_ending": "closing",
}


def _to_trillion(v: str | None) -> float | None:
    """DART 공시 금액 (원 단위 문자열) → 조원 (반올림 1자리)."""
    if v is None or v == "" or v == "-":
        return None
    try:
        x = int(v.replace(",", "").strip())
        return round(x / 1_000_000_000_000, 2)
    except (ValueError, AttributeError):
        return None


def _to_billion(v: str | None) -> float | None:
    """DART 금액 → 십억원."""
    if v is None or v == "" or v == "-":
        return None
    try:
        x = int(v.replace(",", "").strip())
        return round(x / 1_000_000_000, 1)
    except (ValueError, AttributeError):
        return None


def _extract_annual(df: pl.DataFrame, stockCode: str) -> dict:
    """한 회사의 5년 연간 데이터 추출."""
    # 사업보고서 (11011) = 연간.  연결(CFS) 우선, 별도(OFS) 폴백.
    c_df = df.filter((pl.col("stockCode") == stockCode) & (pl.col("reprt_code") == "11011"))
    if c_df.is_empty():
        return {}

    # 연결재무제표 우선. 없으면 별도.
    cfs = c_df.filter(pl.col("fs_div") == "CFS")
    use = cfs if not cfs.is_empty() else c_df

    result = {
        "is": {k: [None] * 5 for k in IS_MAP.values()},
        "bs": {
            "assets": {k: [None] * 5 for k in BS_ASSETS.values()},
            "liab": {k: [None] * 5 for k in BS_LIAB.values()},
            "equity": {k: [None] * 5 for k in BS_EQUITY.values()},
            "totals": {k: [None] * 5 for k in BS_TOTALS.values()},
        },
        "cf": {k: None for k in CF_MAP.values()},
    }

    for i, year in enumerate(YEARS):
        yr_df = use.filter(pl.col("bsns_year") == year)
        if yr_df.is_empty():
            continue

        # IS
        for acc_id, out_key in IS_MAP.items():
            rows = yr_df.filter((pl.col("sj_div") == "IS") & (pl.col("account_id_std") == acc_id))
            if not rows.is_empty():
                val = _to_trillion(rows["thstrm_amount"][0])
                result["is"][out_key][i] = val

        # BS — assets
        for acc_id, out_key in BS_ASSETS.items():
            rows = yr_df.filter((pl.col("sj_div") == "BS") & (pl.col("account_id_std") == acc_id))
            if not rows.is_empty():
                val = _to_trillion(rows["thstrm_amount"][0])
                result["bs"]["assets"][out_key][i] = val

        # BS — liab
        for acc_id, out_key in BS_LIAB.items():
            rows = yr_df.filter((pl.col("sj_div") == "BS") & (pl.col("account_id_std") == acc_id))
            if not rows.is_empty():
                val = _to_trillion(rows["thstrm_amount"][0])
                result["bs"]["liab"][out_key][i] = val

        # BS — equity
        for acc_id, out_key in BS_EQUITY.items():
            rows = yr_df.filter((pl.col("sj_div") == "BS") & (pl.col("account_id_std") == acc_id))
            if not rows.is_empty():
                val = _to_trillion(rows["thstrm_amount"][0])
                result["bs"]["equity"][out_key][i] = val

        # BS — totals
        for acc_id, out_key in BS_TOTALS.items():
            rows = yr_df.filter((pl.col("sj_div") == "BS") & (pl.col("account_id_std") == acc_id))
            if not rows.is_empty():
                val = _to_trillion(rows["thstrm_amount"][0])
                result["bs"]["totals"][out_key][i] = val

        # CF — 마지막 년도(2025)만 저장
        if i == len(YEARS) - 1:
            for acc_id, out_key in CF_MAP.items():
                rows = yr_df.filter((pl.col("sj_div") == "CF") & (pl.col("account_id_std") == acc_id))
                if not rows.is_empty():
                    val = _to_trillion(rows["thstrm_amount"][0])
                    result["cf"][out_key] = val

    # opMargin = op / sales * 100
    result["is"]["opMargin"] = []
    for i in range(5):
        op = result["is"]["op"][i]
        sales = result["is"]["sales"][i]
        if op is not None and sales and sales > 0:
            result["is"]["opMargin"].append(round(op / sales * 100, 1))
        else:
            result["is"]["opMargin"].append(None)

    # ratios: ROE = net / equity * 100, debtRatio = liab / equity * 100
    result["ratios"] = {"roe": [], "debtRatio": []}
    for i in range(5):
        net = result["is"]["net"][i]
        equity = result["bs"]["totals"]["totalEquity"][i]
        liab = result["bs"]["totals"]["totalLiab"][i]
        if net is not None and equity and equity > 0:
            result["ratios"]["roe"].append(round(net / equity * 100, 1))
        else:
            result["ratios"]["roe"].append(None)
        if liab is not None and equity and equity > 0:
            result["ratios"]["debtRatio"].append(round(liab / equity * 100, 1))
        else:
            result["ratios"]["debtRatio"].append(None)

    # CF fxEffect = closing - opening - op - inv - fin
    cf = result["cf"]
    if all(cf.get(k) is not None for k in ("opening", "closing", "op", "inv", "fin")):
        cf["fx"] = round(cf["closing"] - cf["opening"] - cf["op"] - cf["inv"] - cf["fin"], 2)
    else:
        cf["fx"] = 0.0

    return result


def main() -> int:
    print(f"[finance.json 빌드] loading {SRC}...", flush=True)
    t0 = time.time()

    # 전체 parquet 을 한 번에 로드 — 스키마 확인 완료
    df = pl.read_parquet(SRC)
    print(f"  shape: {df.shape}, loaded in {time.time() - t0:.1f}s", flush=True)

    # stockCode 유효 (제로패딩 6자리) 만 필터
    df = df.filter(pl.col("stockCode").str.len_chars() == 6)

    # 필요 컬럼만 select
    df = df.select(
        [
            "stockCode",
            "bsns_year",
            "reprt_code",
            "sj_div",
            "account_id_std",
            "fs_div",
            "thstrm_amount",
        ]
    )
    print(f"  filtered shape: {df.shape}", flush=True)

    # 중복 제거 — 같은 (stockCode, year, reprt, sj_div, account, fs_div) 에 여러 행 존재 가능
    df = df.unique(
        subset=["stockCode", "bsns_year", "reprt_code", "sj_div", "account_id_std", "fs_div"],
        keep="first",
    )

    stockCodes = sorted(df["stockCode"].unique().to_list())
    print(f"  unique stockCodes: {len(stockCodes)}", flush=True)

    companies = {}
    t1 = time.time()
    for i, code in enumerate(stockCodes, 1):
        data = _extract_annual(df, code)
        if data:
            companies[code] = data
        if i % 500 == 0:
            rate = i / (time.time() - t1)
            print(f"  [{i}/{len(stockCodes)}] {rate:.0f}/s", flush=True)

    output = {
        "version": "v16",
        "years": YEARS,
        "companies": companies,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")

    size_mb = OUT.stat().st_size / 1024 / 1024
    elapsed = time.time() - t0
    print(
        f"완료: {len(companies)}사, {size_mb:.1f}MB, {elapsed:.0f}초 → {OUT}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
