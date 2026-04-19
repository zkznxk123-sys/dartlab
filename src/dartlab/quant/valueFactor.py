"""가치/수익성 팩터 — book-based 횡단면 z-score.

⚠️ 한계 명시:
- 시가총액 데이터가 dartlab에 아직 수집돼 있지 않아 (stockTotal apiType 미수집)
  진짜 PBR/PER/PSR을 산출하지 못한다.
- 이 모듈은 시가총액 없이도 만들 수 있는 book-based 지표만 횡단면 z-score로 제공.
- 따라서 함수명은 "value"이지만 실제로는 **수익성/효율성 복합** 지표에 가깝다.
- 시총 인프라가 들어오면 진짜 PBR/PER/PSR 추가 예정 (audit factor.md/value.md 참조).

학술 근거:
- Fama & French (1992, 2015): book-equity 기반 BM 팩터
- Lakonishok et al. (1994): Contrarian Investment, Extrapolation, and Risk
- Asness, Frazzini, Pedersen (2013): Value and Momentum Everywhere

이전 버전(2026-04-06 이전)은 절대값 임계 기반으로 60%가 deep_value로 분류됐고
한국 대표 가치주(KB금융/신한금융)가 growth로 분류되는 명백한 오분류가 있었다.
이번 재구현은 횡단면 백분위 z-score로 교체.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.core.finance.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import (
    extract_account,
    fetch_ohlcv,
    load_scan_parquet,
    ohlcv_to_arrays,
    resolve_market,
)
from dartlab.quant.qualityFactor import _is_financial

log = logging.getLogger(__name__)


_UNIVERSE_CACHE: dict[tuple[str, str], dict[str, list[float]]] = {}


def _build_universe(market: str, year: str) -> dict[str, list[float]]:
    """전종목 단년도 value 지표 분포 (횡단면 z용)."""
    cache_key = (market, year)
    if cache_key in _UNIVERSE_CACHE:
        return _UNIVERSE_CACHE[cache_key]

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {}
    annual = extractAnnualConsolidated(lf.collect())
    edgar = isEdgarSchema(annual)
    year_col = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    snap = annual.filter(pl.col(year_col) == year_val)
    if snap.is_empty():
        return {}

    out = {
        "earningsToBook": [],
        "salesToBook": [],
        "bookToAsset": [],
    }
    codes = snap.get_column("stockCode").unique().to_list()
    for code in codes:
        if not isinstance(code, str):
            continue
        if _is_financial(code):
            continue
        stock = snap.filter(pl.col("stockCode") == code)
        equity = extract_account(stock, "total_equity")
        assets = extract_account(stock, "total_assets")
        ni = extract_account(stock, "net_income")
        sales = extract_account(stock, "sales")
        if not equity or equity <= 0:
            continue
        if ni is not None:
            out["earningsToBook"].append(ni / equity)
        if sales is not None:
            out["salesToBook"].append(sales / equity)
        if assets and assets > 0:
            out["bookToAsset"].append(equity / assets)

    _UNIVERSE_CACHE[cache_key] = out
    return out


def _zscore(value: float, all_values: list[float]) -> float:
    import numpy as np

    arr = np.array([v for v in all_values if v is not None])
    if len(arr) < 10:
        return 0.0
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    if sigma == 0:
        return 0.0
    z = (value - mu) / sigma
    return float(max(-3, min(3, z)))


def calcValue(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """Value/yield 신호 — book-based 횡단면 z-score.

    ⚠️ PBR/PER/PSR 미산출 — 시가총액 데이터 부재. earningsToBook(=ROE),
    salesToBook(=AssetTurnover proxy), bookToAsset(=레버리지 역수)을 z화.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".

    Returns:
        dict — components, valueScore, valueGrade, limitation note.
    """
    market = resolve_market(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    if _is_financial(stockCode):
        result["sector"] = "financial"
        result["grade"] = None
        result["info"] = "금융업은 일반 가치 산식 부적절"
        return result

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}

    try:
        snap = extractAnnualConsolidated(lf.collect())
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.ComputeError) as e:
        return {**result, "error": str(e)}
    if snap.is_empty():
        return {**result, "error": "연결 4분기 데이터 없음"}

    edgar = isEdgarSchema(snap)
    year_col = "fy" if edgar else "bsns_year"
    year_counts = snap.group_by(year_col).len().sort(year_col, descending=True)
    yr = None
    for row in year_counts.iter_rows(named=True):
        if row["len"] >= 1000:
            yr = row[year_col]
            break
    if yr is None:
        return {**result, "error": "충분한 universe 연도 없음"}

    snap_yr = snap.filter(pl.col(year_col) == yr)
    stock = snap_yr.filter(pl.col("stockCode") == stockCode)
    if stock.is_empty():
        # 회계연도 비표준 종목 (예: NVDA fy=2026, 1월결산) — 해당 종목의 최신 fy 로 fallback.
        company_years = (
            snap.filter(pl.col("stockCode") == stockCode).select(year_col).unique().to_series().to_list()
        )
        if not company_years:
            return {**result, "error": f"{stockCode} scan parquet 데이터 없음"}
        yr = max(company_years)
        snap_yr = snap.filter(pl.col(year_col) == yr)
        stock = snap_yr.filter(pl.col("stockCode") == stockCode)
        result["year"] = str(yr)
        if stock.is_empty():
            return {**result, "error": f"{yr} 데이터 없음"}

    equity = extract_account(stock, "total_equity")
    assets = extract_account(stock, "total_assets")
    ni = extract_account(stock, "net_income")
    sales = extract_account(stock, "sales")

    if not equity or equity <= 0:
        return {**result, "error": "자본총계 없음"}

    result["year"] = str(yr)
    components: dict = {}
    if ni is not None:
        components["earningsToBook"] = round(ni / equity, 4)  # = ROE
    if sales is not None:
        components["salesToBook"] = round(sales / equity, 4)
    if assets and assets > 0:
        components["bookToAsset"] = round(equity / assets, 4)

    # 가격은 참고용 (시총 산출 불가하지만 사용자에게 노출)
    try:
        ohlcv = fetch_ohlcv(stockCode)
        if ohlcv is not None and not ohlcv.is_empty():
            arr = ohlcv_to_arrays(ohlcv)
            if "close" in arr and len(arr["close"]) > 0:
                components["latestPrice"] = round(float(arr["close"][-1]), 2)
    except (ValueError, KeyError, OSError, AttributeError, IndexError):
        pass

    result["components"] = components

    universe = _build_universe(market, str(yr))

    zs: list[float] = []
    if "earningsToBook" in components:
        zs.append(_zscore(components["earningsToBook"], universe["earningsToBook"]))
    if "salesToBook" in components:
        zs.append(_zscore(components["salesToBook"], universe["salesToBook"]))
    if "bookToAsset" in components:
        zs.append(_zscore(components["bookToAsset"], universe["bookToAsset"]))

    if zs:
        score = sum(zs) / len(zs)
    else:
        score = 0.0
    result["valueScore"] = round(float(score), 4)

    if score >= 1.5:
        result["valueGrade"] = "high_yield"
    elif score >= 0.5:
        result["valueGrade"] = "above_avg"
    elif score >= -0.5:
        result["valueGrade"] = "average"
    elif score >= -1.5:
        result["valueGrade"] = "below_avg"
    else:
        result["valueGrade"] = "low_yield"

    result["limitation"] = (
        "PBR/PER/PSR 미산출 — 시가총액 데이터 부재. "
        "현재는 book-based 수익성/효율성 복합 지표 (이름이 'value'이지만 진짜 가치 팩터 아님)."
    )

    return result
