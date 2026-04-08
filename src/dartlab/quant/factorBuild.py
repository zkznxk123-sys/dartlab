"""횡단면 팩터 시계열 빌드 — 진짜 시가총액 기반 SMB/HML/RMW/CMA.

발행주식수가 `data/dart/scan/sharesOutstanding.parquet` 으로 수집된 뒤
size = 시가총액(보통주), BM = bookEquity / marketCap 으로 정의한다.

- Fama-French 5: SIZE = 시가총액, BM = book / market
- RMW = ROE 5분위
- CMA = ΔAssets / Assets 5분위

발행주식수 프리빌드가 없으면 (예: EDGAR 측 미수집) book-equity proxy 로
fallback 한다. notes 에 어떤 정의를 사용했는지 명시한다.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.quant._helpers import (
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
    counts = snap.group_by("bsns_year").len().sort("bsns_year", descending=True)
    for row in counts.iter_rows(named=True):
        if row["len"] >= min_count:
            return row["bsns_year"]
    return None


def _load_market_caps(market: str) -> dict[str, float]:
    """전 종목 최신 시가총액 dict (보통주 기준).

    sharesOutstanding × 최신 종가. 없으면 빈 dict.
    """
    from dartlab.gather.marketCap import marketCapAll

    lf = marketCapAll(market)
    if lf is None:
        return {}
    try:
        df = lf.collect()
    except (Exception,):  # noqa: BLE001 — polars 다양한 에러
        return {}
    if df.is_empty():
        return {}

    caps: dict[str, float] = {}
    for row in df.iter_rows(named=True):
        code = row["stock_code"]
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


def _build_universe_metrics(market: str, year: str) -> dict[str, dict[str, float]]:
    """전종목 단년도 펀더멘털 dict.

    Returns:
        {stockCode: {bookEquity, totalAssets, netIncome, roe, bookRatio, assetGrowth, marketCap, bm}}
    """
    caps = _load_market_caps(market)
    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {}

    snap = lf.filter(pl.col("fs_nm").str.contains("연결")).filter(pl.col("reprt_nm").str.contains("4분기")).collect()
    if snap.is_empty():
        return {}

    cur = snap.filter(pl.col("bsns_year") == year)
    # 전기 (asset growth용)
    try:
        prev_year = str(int(year) - 1)
    except ValueError:
        prev_year = None
    prev = snap.filter(pl.col("bsns_year") == prev_year) if prev_year else None

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

        mc = caps.get(code)
        bm = (equity / mc) if mc and mc > 0 else None

        out[code] = {
            "bookEquity": float(equity),
            "totalAssets": float(assets),
            "netIncome": float(ni) if ni is not None else None,
            "roe": float(roe) if roe is not None else None,
            "bookRatio": float(book_ratio),
            "assetGrowth": float(asset_growth) if asset_growth is not None else None,
            "marketCap": float(mc) if mc is not None else None,
            "bm": float(bm) if bm is not None else None,
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
        if o is None or o.is_empty():
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
    snap = lf.filter(pl.col("fs_nm").str.contains("연결")).filter(pl.col("reprt_nm").str.contains("4분기")).collect()
    year = _latest_year(snap)
    if year is None:
        return None

    metrics = _build_universe_metrics(market, year)
    if len(metrics) < 100:
        return None

    # 5분위 포트폴리오 — 시총 기반 SMB, 진짜 BM (book/market)
    have_caps = sum(1 for m in metrics.values() if m.get("marketCap")) >= 100
    have_bm = sum(1 for m in metrics.values() if m.get("bm")) >= 100
    size_key = "marketCap" if have_caps else "bookEquity"
    bm_key = "bm" if have_bm else "bookRatio"
    small, big = _quintile_portfolios(metrics, size_key, reverse=False)
    high_bm, low_bm = _quintile_portfolios(metrics, bm_key, reverse=True)
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
