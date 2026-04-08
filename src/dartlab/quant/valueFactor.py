"""가치 팩터 — 진짜 PBR/PER/PSR 횡단면 z-score.

시가총액 인프라(`gather/marketCap.py` + `data/dart/scan/sharesOutstanding.parquet`)가
들어오면서 진짜 BM (book/market), EP (earnings/price), SP (sales/price) 산출 가능.

학술 근거:
- Fama & French (1992, 2015): book-to-market 팩터 (HML)
- Lakonishok et al. (1994): Contrarian Investment, Extrapolation, and Risk
- Asness, Frazzini, Pedersen (2013): Value and Momentum Everywhere

`bm = book_equity / marketCap`, `ep = net_income / marketCap`, `sp = sales / marketCap`.
모두 yield 형태(클수록 저평가)로 통일 후 횡단면 z-score 평균.

금융업(은행/증권/보험)은 book/earnings 의미가 다르므로 sector="financial" 라벨로 skip.
시총 부재인 종목은 None 반환 (sharesOutstanding 누락).
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.quant._helpers import (
    extract_account,
    fetch_ohlcv,
    load_scan_parquet,
    ohlcv_to_arrays,
    resolve_market,
)
from dartlab.quant.qualityFactor import _is_financial

log = logging.getLogger(__name__)


_UNIVERSE_CACHE: dict[tuple[str, str], dict[str, dict]] = {}


def _load_market_caps(market: str) -> dict[str, float]:
    """전 종목 최신 보통주 시가총액 dict.

    sharesOutstanding × 가장 최근 종가. 시총 인프라가 없으면 빈 dict.
    """
    from dartlab.gather.marketCap import marketCapAll

    lf = marketCapAll(market)
    if lf is None:
        return {}
    try:
        df = lf.collect()
    except (pl.exceptions.PolarsError, OSError):
        return {}
    if df.is_empty():
        return {}

    caps: dict[str, float] = {}
    for row in df.iter_rows(named=True):
        code = row.get("stock_code")
        shares = row.get("outstandingShares")
        if not code or shares is None or shares <= 0:
            continue
        try:
            ohlcv = fetch_ohlcv(code)
        except (ValueError, KeyError, OSError, AttributeError, RuntimeError):
            continue
        if ohlcv is None or ohlcv.is_empty():
            continue
        cl = ohlcv_to_arrays(ohlcv).get("close")
        if cl is None or len(cl) == 0:
            continue
        last = float(cl[-1])
        if last <= 0:
            continue
        caps[code] = last * float(shares)
    return caps


def _build_universe(market: str, year: str) -> dict[str, dict]:
    """전종목 단년도 value 지표 분포 — 진짜 BM/EP/SP (시총 기반).

    Returns:
        {
            "bm":  list[float],   # book/market = equity/marketCap
            "ep":  list[float],   # earnings/market
            "sp":  list[float],   # sales/market
            "caps": dict[code, marketCap],  # 단일종목 조회용
        }
    """
    cache_key = (market, year)
    if cache_key in _UNIVERSE_CACHE:
        return _UNIVERSE_CACHE[cache_key]

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {"bm": [], "ep": [], "sp": [], "caps": {}}
    snap = (
        lf.filter(pl.col("fs_nm").str.contains("연결"))
        .filter(pl.col("reprt_nm").str.contains("4분기"))
        .filter(pl.col("bsns_year") == year)
        .collect()
    )
    if snap.is_empty():
        return {"bm": [], "ep": [], "sp": [], "caps": {}}

    caps = _load_market_caps(market)

    out: dict[str, list] = {"bm": [], "ep": [], "sp": []}
    codes = snap.get_column("stockCode").unique().to_list()
    for code in codes:
        if not isinstance(code, str):
            continue
        if _is_financial(code):
            continue
        mc = caps.get(code)
        if mc is None or mc <= 0:
            continue
        stock = snap.filter(pl.col("stockCode") == code)
        equity = extract_account(stock, "total_equity")
        ni = extract_account(stock, "net_income")
        sales = extract_account(stock, "sales")
        if equity and equity > 0:
            out["bm"].append(equity / mc)
        if ni is not None:
            out["ep"].append(ni / mc)
        if sales is not None:
            out["sp"].append(sales / mc)

    out["caps"] = caps
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


def analyze_value(stockCode: str, *, market: str = "auto", crossSection: bool = False, **kwargs) -> dict:
    """Value 팩터 — 진짜 PBR/PER/PSR 산출 (시총 기반).

    기본(빠름): 단일 종목 multiples (PBR/PER/PSR + yields).
    `crossSection=True`: 전종목 횡단면 z-score (느림 — 처음 호출 시 universe 빌드).

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".
        crossSection: True면 횡단면 z-score 계산 (universe 캐시 있으면 빠름).

    Returns:
        dict — pbr, per, psr (multiples), bm, ep, sp (yields),
               valueScore (crossSection=True 시), valueGrade.
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
        snap = (
            lf.filter(pl.col("fs_nm").str.contains("연결")).filter(pl.col("reprt_nm").str.contains("4분기")).collect()
        )
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.ComputeError) as e:
        return {**result, "error": str(e)}
    if snap.is_empty():
        return {**result, "error": "연결 4분기 데이터 없음"}

    year_counts = snap.group_by("bsns_year").len().sort("bsns_year", descending=True)
    yr = None
    for row in year_counts.iter_rows(named=True):
        if row["len"] >= 1000:
            yr = row["bsns_year"]
            break
    if yr is None:
        return {**result, "error": "충분한 universe 연도 없음"}

    snap_yr = snap.filter(pl.col("bsns_year") == yr)
    stock = snap_yr.filter(pl.col("stockCode") == stockCode)
    if stock.is_empty():
        return {**result, "error": f"{yr} 데이터 없음"}

    equity = extract_account(stock, "total_equity")
    ni = extract_account(stock, "net_income")
    sales = extract_account(stock, "sales")

    if not equity or equity <= 0:
        return {**result, "error": "자본총계 없음"}

    # 시총 — 단일 종목 빠른 경로 (universe 빌드 X)
    from dartlab.gather.marketCap import marketCapSnapshot

    snap_mc = marketCapSnapshot(stockCode, market=market)
    mc = float(snap_mc["marketCap"]) if snap_mc and snap_mc.get("marketCap") else None
    if mc is None or mc <= 0:
        return {**result, "error": "시가총액 없음 (sharesOutstanding 또는 종가 부재)"}

    result["year"] = str(yr)
    result["marketCap"] = round(mc, 0)

    # multiples (가치 평가 배수)
    multiples: dict = {}
    yields: dict = {}

    multiples["pbr"] = round(mc / equity, 4)
    yields["bm"] = round(equity / mc, 6)

    if ni is not None and ni > 0:
        multiples["per"] = round(mc / ni, 4)
    if ni is not None:
        yields["ep"] = round(ni / mc, 6)

    if sales is not None and sales > 0:
        multiples["psr"] = round(mc / sales, 4)
    if sales is not None:
        yields["sp"] = round(sales / mc, 6)

    result["multiples"] = multiples
    result["yields"] = yields

    # 횡단면 z-score (옵션) — universe 캐시가 없으면 빌드 (~수 분, OHLCV 반복 fetch)
    if crossSection:
        universe = _build_universe(market, str(yr))
        zs: list[float] = []
        if "bm" in yields and universe.get("bm"):
            zs.append(_zscore(yields["bm"], universe["bm"]))
        if "ep" in yields and universe.get("ep"):
            zs.append(_zscore(yields["ep"], universe["ep"]))
        if "sp" in yields and universe.get("sp"):
            zs.append(_zscore(yields["sp"], universe["sp"]))

        score = sum(zs) / len(zs) if zs else 0.0
        result["valueScore"] = round(float(score), 4)
        result["universeSize"] = len(universe.get("bm", []))

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
    else:
        # 단일종목 단독 grade — 절대 PBR 임계
        pbr = multiples.get("pbr")
        if pbr is None:
            result["valueGrade"] = None
        elif pbr < 1.0:
            result["valueGrade"] = "deep_value"
        elif pbr < 1.5:
            result["valueGrade"] = "value"
        elif pbr < 3.0:
            result["valueGrade"] = "neutral"
        elif pbr < 5.0:
            result["valueGrade"] = "growth"
        else:
            result["valueGrade"] = "expensive"

    return result
