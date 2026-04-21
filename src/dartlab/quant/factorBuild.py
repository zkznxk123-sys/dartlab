"""횡단면 팩터 시계열 빌드 — Book-based SMB/HML/RMW/CMA.

진짜 시가총액 데이터가 dartlab에 아직 수집돼 있지 않아 (stockTotal apiType 미수집)
**자본총계(book equity)를 size proxy로 사용한다.**

학술적 정확성:
- Fama-French 원본은 시총 기반 SMB. 자본총계 size는 differ하지만 한국 중소형주
  스크리닝에서는 실용적 근사로 사용 가능 (Bali et al. 2016 등 다수 한국 시장
  연구가 size proxy로 자본총계를 채택).
- HML은 본래 BM = book/market인데 이번엔 자본/자산 비율(equity/assets)을 사용 →
  엄밀히는 자본구조 팩터. 시총 데이터가 들어오면 진짜 BM으로 교체.
- RMW = ROE 5분위 (Asness 정의와 일치)
- CMA = 전기 대비 자산성장률(ΔAssets/Assets) 5분위 (Fama-French 5 정의)

이 모듈은 audit에서 발견한 가짜 변동성 합성 프록시를 대체한다 (factor.md 참조).

빌드된 시계열은 캐시되며, factor.py의 analyze_factor가 회귀 입력으로 사용한다.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.core.finance.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import (
from dartlab.core.polarsUtil import isEmptyDf
    extract_account,
    fetch_ohlcv,
    load_scan_parquet,
    ohlcv_to_arrays,
)

log = logging.getLogger(__name__)


_FACTOR_CACHE: dict[tuple[str, str], dict] = {}
_PORTFOLIO_CACHE: dict[tuple[str, str, int], np.ndarray] = {}


def _latest_year(snap: pl.DataFrame, min_count: int = 1000) -> str | None:
    """충분한 universe를 가진 가장 최근 연도."""
    if snap.is_empty():
        return None
    year_col = "fy" if isEdgarSchema(snap) else "bsns_year"
    counts = snap.group_by(year_col).len().sort(year_col, descending=True)
    for row in counts.iter_rows(named=True):
        if row["len"] >= min_count:
            y = row[year_col]
            return str(y) if y is not None else None
    return None


def _build_universe_metrics(market: str, year: str) -> dict[str, dict[str, float]]:
    """전종목 단년도 펀더멘털 dict.

    Returns:
        {stockCode: {bookEquity, totalAssets, netIncome, roe, bookRatio, assetGrowth}}
    """
    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {}

    snap = extractAnnualConsolidated(lf.collect())
    if snap.is_empty():
        return {}

    edgar = isEdgarSchema(snap)
    year_col = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    cur = snap.filter(pl.col(year_col) == year_val)
    # 전기 (asset growth용)
    try:
        prev_year_val = int(year) - 1
    except ValueError:
        prev_year_val = None
    if prev_year_val is not None:
        pv = prev_year_val if edgar else str(prev_year_val)
        prev = snap.filter(pl.col(year_col) == pv)
    else:
        prev = None

    out: dict[str, dict[str, float]] = {}
    codes = cur.get_column("stockCode").unique().to_list()
    for code in codes:
        if not isinstance(code, str):
            continue
        stock = cur.filter(pl.col("stockCode") == code)
        if stock.is_empty():
            continue

        equity = extract_account(stock, "total_equity")
        assets = extract_account(stock, "total_assets")
        ni = extract_account(stock, "net_income")
        if not equity or not assets or equity <= 0 or assets <= 0:
            continue

        roe = (ni / equity) if ni is not None else None
        book_ratio = equity / assets

        asset_growth = None
        if prev is not None:
            prev_stock = prev.filter(pl.col("stockCode") == code)
            if not prev_stock.is_empty():
                prev_assets = extract_account(prev_stock, "total_assets")
                if prev_assets and prev_assets > 0:
                    asset_growth = (assets - prev_assets) / prev_assets

        out[code] = {
            "bookEquity": float(equity),
            "totalAssets": float(assets),
            "netIncome": float(ni) if ni is not None else None,
            "roe": float(roe) if roe is not None else None,
            "bookRatio": float(book_ratio),
            "assetGrowth": float(asset_growth) if asset_growth is not None else None,
        }
    return out


def _quintile_portfolios(metrics: dict[str, dict[str, float]], key: str, reverse: bool) -> tuple[list[str], list[str]]:
    """지표 5분위 → 상위 20% / 하위 20% 종목군.

    reverse=True면 상위가 작은 값.
    """
    items = [(c, m[key]) for c, m in metrics.items() if m.get(key) is not None]
    if len(items) < 50:
        return [], []
    items.sort(key=lambda x: x[1], reverse=reverse)
    n = len(items)
    cutoff = max(int(n * 0.2), 10)
    top = [c for c, _ in items[:cutoff]]
    bot = [c for c, _ in items[-cutoff:]]
    return top, bot


def _portfolio_returns(codes: list[str], market: str, year: str, max_n: int = 30) -> np.ndarray | None:
    """종목 리스트의 동일가중 평균 일별 log return 시계열.

    캐시: (market, year, hash(codes))
    """
    if not codes:
        return None
    key = (market, year, hash(tuple(sorted(codes[:max_n]))))
    if key in _PORTFOLIO_CACHE:
        return _PORTFOLIO_CACHE[key]

    rets = []
    for c in codes[:max_n]:
        try:
            o = fetch_ohlcv(c)
        except (ValueError, KeyError, OSError, AttributeError, RuntimeError):
            continue
        if isEmptyDf(o):
            continue
        cl = ohlcv_to_arrays(o).get("close")
        if cl is None or len(cl) < 60:
            continue
        rets.append(np.diff(np.log(cl)))

    if len(rets) < 5:
        _PORTFOLIO_CACHE[key] = None
        return None
    ml = min(len(r) for r in rets)
    panel = np.column_stack([r[-ml:] for r in rets])
    avg = panel.mean(axis=1)
    _PORTFOLIO_CACHE[key] = avg
    return avg


def build_factors(market: str = "KR") -> dict | None:
    """진짜 횡단면 SMB/HML/RMW/CMA 시계열 빌드 (캐시됨).

    Returns:
        dict with keys: year, universe, smb, hml, rmw, cma (np.ndarray),
                        notes (proxy 사용 명시)
        또는 None
    """
    cache_key = (market, "latest")
    if cache_key in _FACTOR_CACHE:
        return _FACTOR_CACHE[cache_key]

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return None
    snap = extractAnnualConsolidated(lf.collect())
    year = _latest_year(snap)
    if year is None:
        return None

    metrics = _build_universe_metrics(market, year)
    if len(metrics) < 100:
        return None

    # 5분위 포트폴리오
    small, big = _quintile_portfolios(metrics, "bookEquity", reverse=False)
    high_bm, low_bm = _quintile_portfolios(metrics, "bookRatio", reverse=True)
    high_roe, low_roe = _quintile_portfolios(metrics, "roe", reverse=True)
    low_ag, high_ag = _quintile_portfolios(metrics, "assetGrowth", reverse=False)
    # CMA = conservative(low growth) - aggressive(high growth)

    # 시계열
    s_ret = _portfolio_returns(small, market, year)
    b_ret = _portfolio_returns(big, market, year)
    h_ret = _portfolio_returns(high_bm, market, year)
    l_ret = _portfolio_returns(low_bm, market, year)
    hr_ret = _portfolio_returns(high_roe, market, year)
    lr_ret = _portfolio_returns(low_roe, market, year)
    cn_ret = _portfolio_returns(low_ag, market, year)
    ag_ret = _portfolio_returns(high_ag, market, year)

    if any(x is None for x in [s_ret, b_ret, h_ret, l_ret]):
        return None

    # 길이 정규화 (가장 짧은 시계열 기준)
    arrs = [s_ret, b_ret, h_ret, l_ret]
    if hr_ret is not None and lr_ret is not None:
        arrs.extend([hr_ret, lr_ret])
    if cn_ret is not None and ag_ret is not None:
        arrs.extend([cn_ret, ag_ret])
    ml = min(len(a) for a in arrs)

    smb = s_ret[-ml:] - b_ret[-ml:]
    hml = h_ret[-ml:] - l_ret[-ml:]
    rmw = (hr_ret[-ml:] - lr_ret[-ml:]) if (hr_ret is not None and lr_ret is not None) else None
    cma = (cn_ret[-ml:] - ag_ret[-ml:]) if (cn_ret is not None and ag_ret is not None) else None

    result = {
        "year": str(year),
        "market": market,
        "universe": len(metrics),
        "n_obs": int(ml),
        "smb": smb,
        "hml": hml,
        "rmw": rmw,
        "cma": cma,
        "smallN": len(small),
        "bigN": len(big),
        "highBmN": len(high_bm),
        "lowBmN": len(low_bm),
        "notes": (
            "SIZE proxy = book equity (시가총액 데이터 미수집). "
            "BM proxy = equity/assets (시가총액 부재로 진짜 BM 불가)."
        ),
    }
    _FACTOR_CACHE[cache_key] = result
    return result
