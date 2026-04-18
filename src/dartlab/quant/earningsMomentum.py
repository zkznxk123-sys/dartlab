"""이익 모멘텀 — SUE + PEAD.

학술 근거: Ball & Brown (1968), Bernard & Thomas (1989).
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.core.finance.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import load_scan_parquet, resolve_market

log = logging.getLogger(__name__)


def _parse(val) -> float | None:
    """문자열/숫자 → float. core SSOT 사용."""
    if isinstance(val, (int, float)):
        return float(val)
    from dartlab.core.finance.helpers import parseNumStr

    return parseNumStr(val)


def calcEarnings(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """SUE + PEAD 이익 모멘텀 분석.

    Standardized Unexpected Earnings 로 서프라이즈 크기를 측정하고,
    PEAD(Post-Earnings Announcement Drift) 신호 강도를 판정한다.

    Parameters
    ----------
    stockCode : str
        종목코드.
    market : str
        "KR" | "US" | "auto". 기본 "auto".

    Returns
    -------
    dict
        stockCode : str — 종목코드
        market : str — 시장
        sue : float — Standardized Unexpected Earnings (배)
        latestOpIncome : float — 최근 영업이익 (원)
        prevMean : float — 과거 평균 영업이익 (원)
        peadSignal : str — "positive_drift" | "negative_drift" | "mild_positive" | "mild_negative" | "none"
        peadStrength : str — "strong" | "moderate" | "weak"
        earningsTrend : str — "consistent_growth" | "mostly_growing" | "mostly_declining" | "mixed"
        opIncomeHistory : dict[str, float] — 연도별 영업이익 (원)
    """
    market = resolve_market(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}
    try:
        full = lf.filter(pl.col("stockCode") == stockCode).collect()
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        return {**result, "error": str(e)}
    if full.is_empty():
        return {**result, "error": "영업이익 데이터 없음"}

    edgar = isEdgarSchema(full)
    annual = extractAnnualConsolidated(full)

    yearly: dict[str, float] = {}
    if edgar:
        # EDGAR: operating_profit 컬럼 직접 사용
        year_col = "fy"
        for row in annual.iter_rows(named=True):
            y = str(row.get(year_col, ""))
            v = row.get("operating_profit")
            if y and v is not None:
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    continue
                if y not in yearly or abs(v) > abs(yearly.get(y, 0)):
                    yearly[y] = v
    else:
        # DART: sj_div + account_nm 필터
        stock = annual.filter(
            (pl.col("sj_div") == "IS")
            & pl.col("account_nm").str.contains("영업이익")
        )
        for row in stock.iter_rows(named=True):
            y = row.get("bsns_year")
            v = _parse(row.get("thstrm_amount"))
            if y and v is not None:
                if y not in yearly or abs(v) > abs(yearly.get(y, 0)):
                    yearly[y] = v

    if len(yearly) < 2:
        return {**result, "error": f"연도 부족 ({len(yearly)}개)"}

    yrs = sorted(yearly.keys())
    vals = [yearly[y] for y in yrs]
    result["years"] = yrs
    result["opIncomeHistory"] = {y: v for y, v in zip(yrs, vals)}

    latest = vals[-1]
    prev = np.array(vals[:-1], dtype=np.float64)
    mu = float(np.mean(prev))
    sd = float(np.std(prev, ddof=1)) if len(prev) > 1 else 0

    sue = float((latest - mu) / sd) if sd > 0 else (3.0 if latest > mu else -3.0 if latest < mu else 0.0)
    result["sue"] = round(sue, 4)
    result["latestOpIncome"] = latest
    result["prevMean"] = round(mu, 0)

    if abs(sue) > 2:
        result["peadSignal"] = "positive_drift" if sue > 0 else "negative_drift"
        result["peadStrength"] = "strong"
    elif abs(sue) > 1:
        result["peadSignal"] = "mild_positive" if sue > 0 else "mild_negative"
        result["peadStrength"] = "moderate"
    else:
        result["peadSignal"] = "none"
        result["peadStrength"] = "weak"

    if len(vals) >= 3:
        diffs = [vals[i] - vals[i - 1] for i in range(1, len(vals))]
        pos = sum(1 for d in diffs if d > 0)
        r = pos / len(diffs)
        result["earningsTrend"] = (
            "consistent_growth"
            if r == 1
            else "mostly_growing"
            if r >= 0.7
            else "mostly_declining"
            if r <= 0.3
            else "mixed"
        )
    return result
