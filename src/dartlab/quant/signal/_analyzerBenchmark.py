"""quant/signal/analyzer 벤치마크 + audit 헬퍼.

quant/signal/analyzer.py 의 benchmark/beta/RS/audit 함수 4종을 분리.
identity 보존을 위해 analyzer.py 가 본 모듈에서 re-export 한다.

함수:
- _fetchBenchmark — 시장 지수 OHLCV 수집 (KRX/Yahoo)
- _relativeStrength — 종목 RSI - 시장 RSI
- _calcBeta — OLS β + CAPM + t-stat
- _categoryEdgeAudit — 카테고리 라벨 forward return 통계 검증
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.synth import indicators as ind


def _fetchBenchmark(
    benchmark: str = "KOSPI",
    *,
    stockCode: str | None = None,
    market: str = "auto",
    benchmarkMode: str = "market",
    start: str | None = None,
    end: str | None = None,
    returnMeta: bool = False,
) -> pl.DataFrame | tuple[pl.DataFrame | None, dict] | None:
    """시장 지수 OHLCV 수집.

    KR은 ``quant.benchmark`` SSOT를 통해 KRX 지수 HF 데이터셋을 사용한다.
    기존 테스트와 내부 호출 호환을 위해 기본 반환은 DataFrame 그대로 유지하고,
    ``return_meta=True`` 때만 ``(df, benchmarkUsed)`` 를 반환한다.
    """
    from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

    explicit = None if benchmark in {"KOSPI", "KR"} else benchmark
    if benchmark in {"S&P500", "^GSPC"} and market == "auto":
        market = "US"
    return fetchBenchmarkOhlcv(
        stockCode,
        market=market,
        benchmark=explicit,
        benchmarkMode=benchmarkMode,
        start=start,
        end=end,
        returnMeta=returnMeta,
    )


def _relativeStrength(stockDf: pl.DataFrame, marketDf: pl.DataFrame) -> float | None:
    """종목 RSI - 시장 RSI → 상대강도."""
    s_close = stockDf["close"].to_numpy().astype(np.float64)
    m_close = marketDf["close"].to_numpy().astype(np.float64)

    s_rsi = ind.vrsi(s_close, 14)
    m_rsi = ind.vrsi(m_close, 14)

    last_s = float(s_rsi[-1]) if not np.isnan(s_rsi[-1]) else None
    last_m = float(m_rsi[-1]) if not np.isnan(m_rsi[-1]) else None

    if last_s is not None and last_m is not None:
        return round(last_s - last_m, 1)
    return None


def _calcBeta(stockDf: pl.DataFrame, marketDf: pl.DataFrame) -> dict | None:
    """종목 vs 시장 OLS 베타 + CAPM."""
    s_dates = set(str(d) for d in stockDf["date"].to_list())
    m_dates = set(str(d) for d in marketDf["date"].to_list())
    common = sorted(s_dates & m_dates)

    if len(common) < 30:
        return None

    s_df = stockDf.with_columns(pl.col("date").cast(pl.Utf8).alias("_d")).filter(pl.col("_d").is_in(common)).sort("_d")
    m_df = marketDf.with_columns(pl.col("date").cast(pl.Utf8).alias("_d")).filter(pl.col("_d").is_in(common)).sort("_d")

    sc = s_df["close"].to_numpy().astype(np.float64)
    mc = m_df["close"].to_numpy().astype(np.float64)
    sr = np.diff(sc) / sc[:-1]
    mr = np.diff(mc) / mc[:-1]

    mask = ~(np.isnan(sr) | np.isnan(mr))
    sr, mr = sr[mask], mr[mask]
    if len(sr) < 30:
        return None

    xm, ym = mr.mean(), sr.mean()
    cov = np.sum((mr - xm) * (sr - ym))
    var = np.sum((mr - xm) ** 2)
    beta = cov / var if var > 0 else 0
    alpha = ym - beta * xm

    yhat = alpha + beta * mr
    ss_res = np.sum((sr - yhat) ** 2)
    ss_tot = np.sum((sr - ym) ** 2)
    r_sq = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    n = len(sr)
    t_beta = None
    if n > 2 and var > 0:
        mse = ss_res / (n - 2)
        se_beta = np.sqrt(mse / var)
        if se_beta > 0:
            t_beta = float(beta / se_beta)

    rf = 0.035
    mrp = 0.065
    capm = round((rf + beta * mrp) * 100, 1)

    return {
        "value": float(round(beta, 3)),
        "alpha": float(round(alpha * 252 * 100, 2)),
        "rSquared": float(round(r_sq, 4)),
        "tStat": float(round(t_beta, 2)) if t_beta is not None else None,
        "nObs": len(sr),
        "capm": float(capm),
    }


def _categoryEdgeAudit(
    stockCodes: list[str],
    category: str,
    *,
    horizons: tuple[int, ...] = (5, 10, 20),
    minSignals: int = 30,
    ratioThreshold: float = 1.3,
    tThreshold: float = 1.96,
) -> dict[str, dict]:
    """카테고리 라벨 × horizon → forward return 통계 우위 검증 (Phase 5).

    5종목 5년 OHLCV 로 각 라벨이 통계적으로 의미 있는지 확인.
    fail 라벨은 코드에서 자동 제거해야 한다.
    """
    from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays
    from dartlab.quant.signal._analyzerCategories import (
        _categoryMomentum,
        _categoryPattern,
        _categoryTrend,
        _categoryVolatility,
        _categoryVolume,
    )

    cat_fn = {
        "trend": _categoryTrend,
        "momentum": _categoryMomentum,
        "volatility": _categoryVolatility,
        "volume": _categoryVolume,
        "pattern": _categoryPattern,
    }[category]

    label_returns: dict[str, dict[int, list[float]]] = {}
    baseline_returns: dict[int, list[float]] = {h: [] for h in horizons}

    for code in stockCodes:
        ohlcv = fetchOhlcv(code, start="2014-01-01")
        if isEmptyDf(ohlcv):
            continue
        arr = ohlcvToArrays(ohlcv)
        close = arr.get("close")
        high = arr.get("high")
        low = arr.get("low")
        volume = arr.get("volume")
        if close is None or len(close) < 300:
            continue

        n = len(close)
        max_h = max(horizons)

        for t in range(252, n - max_h):
            if category == "pattern":
                sub_df = pl.DataFrame(
                    {
                        "open": close[: t + 1],
                        "high": high[: t + 1],
                        "low": low[: t + 1],
                        "close": close[: t + 1],
                        "volume": volume[: t + 1] if volume is not None else np.zeros(t + 1),
                    }
                )
                cat_result = cat_fn(sub_df)
            elif category == "volume":
                cat_result = cat_fn(
                    close[: t + 1],
                    volume[: t + 1] if volume is not None else np.zeros(t + 1),
                    high[: t + 1],
                    low[: t + 1],
                )
            else:
                cat_result = cat_fn(close[: t + 1], high[: t + 1], low[: t + 1])

            lbl = cat_result.get("label", "")
            if not lbl:
                continue

            if lbl not in label_returns:
                label_returns[lbl] = {h: [] for h in horizons}

            for h in horizons:
                if t + h < n:
                    fwd = (close[t + h] - close[t]) / close[t]
                    label_returns[lbl][h].append(fwd)
                    baseline_returns[h].append(fwd)

    def _welchT(a, b):
        na, nb = len(a), len(b)
        if na < 5 or nb < 5:
            return 0.0
        ma, mb = np.mean(a), np.mean(b)
        va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
        se = math.sqrt(va / na + vb / nb) if (va / na + vb / nb) > 0 else 1e-9
        return (ma - mb) / se

    def _winsorize(arr, lo=0.01, hi=0.99):
        if not arr:
            return arr
        a = np.array(arr)
        q_lo, q_hi = np.quantile(a, lo), np.quantile(a, hi)
        return np.clip(a, q_lo, q_hi).tolist()

    result: dict[str, dict] = {}
    for lbl, h_rets in label_returns.items():
        lbl_result: dict = {"n_signals": sum(len(v) for v in h_rets.values()), "horizon_details": {}}
        passes_any = False
        for h in horizons:
            rets = _winsorize(h_rets.get(h, []))
            base = _winsorize(baseline_returns.get(h, []))
            n_sig = len(rets)
            avg_fwd = float(np.mean(rets)) if rets else 0
            avg_base = float(np.mean(base)) if base else 0
            ratio = avg_fwd / avg_base if abs(avg_base) > 1e-9 else 0
            t_stat = _welchT(rets, base)

            passed = (
                n_sig >= minSignals
                and (abs(ratio) >= ratioThreshold or abs(ratio) <= 1 / ratioThreshold)
                and abs(t_stat) >= tThreshold
            )
            if passed:
                passes_any = True

            lbl_result["horizon_details"][h] = {
                "n": n_sig,
                "avg_forward": round(avg_fwd * 100, 3),
                "baseline": round(avg_base * 100, 3),
                "ratio": round(ratio, 2),
                "t_stat": round(t_stat, 2),
                "pass": passed,
            }

        lbl_result["pass"] = passes_any
        first_h = horizons[0]
        d = lbl_result["horizon_details"].get(first_h, {})
        lbl_result.update(
            {
                f"avg_forward_{first_h}d": d.get("avg_forward", 0),
                f"baseline_{first_h}d": d.get("baseline", 0),
                "ratio": d.get("ratio", 0),
                "t_stat": d.get("t_stat", 0),
            }
        )
        result[lbl] = lbl_result

    return result


__all__ = ["_calcBeta", "_categoryEdgeAudit", "_fetchBenchmark", "_relativeStrength"]
