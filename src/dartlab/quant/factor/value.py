"""가치 팩터 — 진짜 PBR/PER/PSR 횡단면 z-score (Phase B1, 2026-04-24).

KR (Phase B1 정정): KRX OpenAPI ``MKTCAP`` 직접 사용 → 진짜 PBR/PER/PSR 산출.
US: 시총 미수집 → fallback book proxy (earningsToBook/salesToBook/bookToAsset).

학술 근거:
- Fama & French (1992, 2015): BM (book/market) value factor
- Lakonishok et al. (1994): Contrarian Investment
- Asness, Frazzini, Pedersen (2013): Value and Momentum Everywhere

진짜 가치 팩터:
- PBR (Price-to-Book) = marketCap / equity
- PER (Price-to-Earnings) = marketCap / netIncome
- PSR (Price-to-Sales) = marketCap / sales
- 낮을수록 (역수가 높을수록) value 강함 → earningsYield (=1/PER), bookYield (=1/PBR), salesYield (=1/PSR) z-score

이전 (2026-04-06 ~ 04-24) 은 시총 부재로 book proxy 만 — 이름은 value 지만 실제 수익성/효율성 복합.
이번 정정으로 KR 시장은 진짜 가치 팩터 작동.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.core.market import resolveMarket
from dartlab.quant.factor.quality import _isFinancial
from dartlab.quant.screen.dataAccess import (
    extractAccount,
    fetchOhlcv,
    loadScanParquet,
    ohlcvToArrays,
)
from dartlab.synth.scanBridge import extractAnnualConsolidated, isEdgarSchema

log = logging.getLogger(__name__)


_UNIVERSE_CACHE: dict[tuple[str, str], dict[str, list[float]]] = {}


def _fetchYearEndMarketcaps(market: str, year: str) -> dict[str, float]:
    """연도말 시총 (KR 만 — KRX MKTCAP, US 는 빈 dict). factorBuild 와 동일 SSOT."""
    if market != "KR":
        return {}
    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered

        long_df = loadFiltered(start=f"{year}-12-25", end=f"{year}-12-31", adjustment="raw")
        if long_df is None or long_df.is_empty():
            return {}
        latest = (
            long_df.sort("BAS_DD", descending=True).unique(subset=["ISU_CD"], keep="first").select(["ISU_CD", "MKTCAP"])
        )
        return {
            row["ISU_CD"]: float(row["MKTCAP"])
            for row in latest.iter_rows(named=True)
            if row.get("MKTCAP") and row["MKTCAP"] > 0
        }
    except Exception as exc:
        log.warning("valueFactor: 시총 fetch 실패 (year=%s): %s", year, type(exc).__name__)
        return {}


def _buildUniverse(market: str, year: str) -> dict[str, list[float]]:
    """전종목 단년도 value 지표 분포 (횡단면 z용).

    KR: 진짜 PBR/PER/PSR (시총 + DART 재무) + book proxy.
    US: book proxy 만 (시총 미수집).
    """
    cache_key = (market, year)
    if cache_key in _UNIVERSE_CACHE:
        return _UNIVERSE_CACHE[cache_key]

    lf = loadScanParquet("finance", market)
    if lf is None:
        return {}
    annual = extractAnnualConsolidated(lf.collect(engine="streaming"))
    edgar = isEdgarSchema(annual)
    yearCol = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    snap = annual.filter(pl.col(yearCol) == year_val)
    if snap.is_empty():
        return {}

    market_caps = _fetchYearEndMarketcaps(market, year)

    out = {
        "earningsToBook": [],
        "salesToBook": [],
        "bookToAsset": [],
        # 진짜 가치 yield (낮을수록 좋은 PER/PBR/PSR 의 역수 — 큰 z-score = value)
        "earningsYield": [],  # = 1/PER = netIncome / marketCap
        "bookYield": [],  # = 1/PBR = equity / marketCap
        "salesYield": [],  # = 1/PSR = sales / marketCap
    }
    codes = snap.get_column("stockCode").unique().to_list()
    for code in codes:
        if not isinstance(code, str):
            continue
        if _isFinancial(code):
            continue
        stock = snap.filter(pl.col("stockCode") == code)
        equity = extractAccount(stock, "total_equity")
        assets = extractAccount(stock, "total_assets")
        ni = extractAccount(stock, "net_income")
        sales = extractAccount(stock, "sales")
        if not equity or equity <= 0:
            continue
        if ni is not None:
            out["earningsToBook"].append(ni / equity)
        if sales is not None:
            out["salesToBook"].append(sales / equity)
        if assets and assets > 0:
            out["bookToAsset"].append(equity / assets)

        # 진짜 yield (시총 있을 때만)
        mc = market_caps.get(code)
        if mc and mc > 0:
            if ni is not None:
                out["earningsYield"].append(ni / mc)
            out["bookYield"].append(equity / mc)
            if sales is not None:
                out["salesYield"].append(sales / mc)

    _UNIVERSE_CACHE[cache_key] = out
    return out


def _zscore(value: float, allValues: list[float]) -> float:
    import numpy as np

    arr = np.array([v for v in allValues if v is not None])
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
    market = resolveMarket(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    if _isFinancial(stockCode):
        result["sector"] = "financial"
        result["grade"] = None
        result["info"] = "금융업은 일반 가치 산식 부적절"
        return result

    lf = loadScanParquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}

    try:
        snap = extractAnnualConsolidated(lf.collect(engine="streaming"))
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.ComputeError) as e:
        return {**result, "error": str(e)}
    if snap.is_empty():
        return {**result, "error": "연결 4분기 데이터 없음"}

    edgar = isEdgarSchema(snap)
    yearCol = "fy" if edgar else "bsns_year"
    year_counts = snap.group_by(yearCol).len().sort(yearCol, descending=True)
    yr = None
    for row in year_counts.iter_rows(named=True):
        if row["len"] >= 1000:
            yr = row[yearCol]
            break
    if yr is None:
        return {**result, "error": "충분한 universe 연도 없음"}

    snapYr = snap.filter(pl.col(yearCol) == yr)
    stock = snapYr.filter(pl.col("stockCode") == stockCode)
    if stock.is_empty():
        # 회계연도 비표준 종목 (예: NVDA fy=2026, 1월결산) — 해당 종목의 최신 fy 로 fallback.
        company_years = snap.filter(pl.col("stockCode") == stockCode).select(yearCol).unique().to_series().to_list()
        if not company_years:
            return {**result, "error": f"{stockCode} scan parquet 데이터 없음"}
        yr = max(company_years)
        snapYr = snap.filter(pl.col(yearCol) == yr)
        stock = snapYr.filter(pl.col("stockCode") == stockCode)
        result["year"] = str(yr)
        if stock.is_empty():
            return {**result, "error": f"{yr} 데이터 없음"}

    equity = extractAccount(stock, "total_equity")
    assets = extractAccount(stock, "total_assets")
    ni = extractAccount(stock, "net_income")
    sales = extractAccount(stock, "sales")

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

    # 시총 fetch (KR 만 — Phase B1)
    market_caps = _fetchYearEndMarketcaps(market, str(yr))
    mc = market_caps.get(stockCode)
    if mc and mc > 0:
        components["marketCap"] = round(float(mc), 0)
        components["pbr"] = round(mc / equity, 2) if equity > 0 else None
        if ni is not None and ni > 0:
            components["per"] = round(mc / ni, 2)
        if sales is not None and sales > 0:
            components["psr"] = round(mc / sales, 2)
        # yield (역수 — z-score 친화: 높을수록 value)
        if ni is not None:
            components["earningsYield"] = round(ni / mc, 4)
        components["bookYield"] = round(equity / mc, 4)
        if sales is not None:
            components["salesYield"] = round(sales / mc, 4)

    # 가격 참고
    try:
        ohlcv = fetchOhlcv(stockCode)
        if ohlcv is not None and not ohlcv.is_empty():
            arr = ohlcvToArrays(ohlcv)
            if "close" in arr and len(arr["close"]) > 0:
                components["latestPrice"] = round(float(arr["close"][-1]), 2)
    except (ValueError, KeyError, OSError, AttributeError, IndexError):
        pass

    result["components"] = components

    universe = _buildUniverse(market, str(yr))

    zs: list[float] = []
    # 진짜 yield 우선 (시총 있을 때) — KR 만
    has_real = market == "KR" and mc and mc > 0 and universe.get("bookYield")
    if has_real:
        if "earningsYield" in components and universe.get("earningsYield"):
            zs.append(_zscore(components["earningsYield"], universe["earningsYield"]))
        if "bookYield" in components and universe.get("bookYield"):
            zs.append(_zscore(components["bookYield"], universe["bookYield"]))
        if "salesYield" in components and universe.get("salesYield"):
            zs.append(_zscore(components["salesYield"], universe["salesYield"]))
    else:
        # fallback book proxy (US 또는 시총 미가용)
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
    result["isRealValue"] = bool(has_real)

    if score >= 1.5:
        result["valueGrade"] = "deep_value"
    elif score >= 0.5:
        result["valueGrade"] = "value"
    elif score >= -0.5:
        result["valueGrade"] = "neutral"
    elif score >= -1.5:
        result["valueGrade"] = "growth"
    else:
        result["valueGrade"] = "expensive"

    result["notes"] = (
        "진짜 가치 팩터 (KRX 시총 기반 PBR/PER/PSR yield z-score)."
        if has_real
        else "fallback book proxy (시총 미가용). earningsToBook/salesToBook/bookToAsset z-score."
    )

    return result
