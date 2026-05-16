"""종합 기술적 분석 — 25개 지표 계산 + 판단(강세/중립/약세).

OHLCV DataFrame → 지표 DataFrame + 종합 판단 dict.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.signal import generator as sig
from dartlab.quant.signal._analyzerCategories import (
    _categoryMomentum,
    _categoryPattern,
    _categoryTrend,
    _categoryVolatility,
    _categoryVolume,
)
from dartlab.synth import indicators as ind

__all_helpers__ = [
    "_categoryMomentum",
    "_categoryPattern",
    "_categoryTrend",
    "_categoryVolatility",
    "_categoryVolume",
]


def enrichWithIndicators(df: pl.DataFrame) -> pl.DataFrame:
    """OHLCV DataFrame에 25개 기술적 지표를 추가.

    Args:
        df: date, open, high, low, close, volume 컬럼 필수.

    Returns:
        원본 + 지표 컬럼이 추가된 DataFrame.
    """
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)
    volume = df["volume"].to_numpy().astype(np.float64) if "volume" in df.columns else np.zeros(len(close))

    # 추세
    sma20 = ind.vsma(close, 20)
    sma60 = ind.vsma(close, 60)
    sma120 = ind.vsma(close, 120)
    ema12 = ind.vema(close, 12)
    ema26 = ind.vema(close, 26)
    macd_line, macd_signal, macd_hist = ind.vmacd(close)
    adx14 = ind.vadx(high, low, close, 14)
    psar = ind.vpsar(high, low)
    st, st_dir = ind.vsupertrend(high, low, close)

    # 모멘텀
    rsi14 = ind.vrsi(close, 14)
    stoch_k, stoch_d = ind.vstochastic(high, low, close)
    roc12 = ind.vroc(close, 12)
    mom10 = ind.vmomentum(close, 10)
    willR = ind.vwilliamsR(high, low, close, 14)
    cci20 = ind.vcci(high, low, close, 20)
    cmo14 = ind.vcmo(close, 14)

    # 변동성
    bb_upper, bb_middle, bb_lower = ind.vbollinger(close, 20, 2.0)
    atr14 = ind.vatr(high, low, close, 14)
    kelt_upper, kelt_middle, kelt_lower = ind.vkeltner(high, low, close)
    don_upper, don_middle, don_lower = ind.vdonchian(high, low, 20)

    # 거래량
    obv = ind.vobv(close, volume)
    mfi14 = ind.vmfi(high, low, close, volume, 14)
    force13 = ind.vforceIndex(close, volume, 13)
    bull, bear = ind.velderRay(high, low, close, 13)

    return df.with_columns(
        [
            # 추세
            pl.Series("sma20", sma20),
            pl.Series("sma60", sma60),
            pl.Series("sma120", sma120),
            pl.Series("ema12", ema12),
            pl.Series("ema26", ema26),
            pl.Series("macd", macd_line),
            pl.Series("macdSignal", macd_signal),
            pl.Series("macdHist", macd_hist),
            pl.Series("adx", adx14),
            pl.Series("psar", psar),
            pl.Series("supertrend", st),
            pl.Series("stDirection", st_dir),
            # 모멘텀
            pl.Series("rsi", rsi14),
            pl.Series("stochK", stoch_k),
            pl.Series("stochD", stoch_d),
            pl.Series("roc", roc12),
            pl.Series("momentum", mom10),
            pl.Series("williamsR", willR),
            pl.Series("cci", cci20),
            pl.Series("cmo", cmo14),
            # 변동성
            pl.Series("bbUpper", bb_upper),
            pl.Series("bbLower", bb_lower),
            pl.Series("atr", atr14),
            pl.Series("keltUpper", kelt_upper),
            pl.Series("keltLower", kelt_lower),
            pl.Series("donchianUpper", don_upper),
            pl.Series("donchianLower", don_lower),
            # 거래량
            pl.Series("obv", obv),
            pl.Series("mfi", mfi14),
            pl.Series("forceIndex", force13),
            pl.Series("bullPower", bull),
            pl.Series("bearPower", bear),
        ]
    )


def technicalVerdict(
    df: pl.DataFrame,
    *,
    stockCode: str | None = None,
    market: str = "auto",
    benchmark: str | None = None,
    benchmarkMode: str = "market",
) -> dict[str, Any]:
    """OHLCV → 종합 기술적 판단.

    Returns:
        dict with keys: verdict(강세/중립/약세), score(-4~+4),
        rsi, aboveSma20, aboveSma60, bbPosition, signals, ...
    """
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)

    rsi = ind.vrsi(close, 14)
    sma20 = ind.vsma(close, 20)
    sma60 = ind.vsma(close, 60)
    bb_upper, _, bb_lower = ind.vbollinger(close)
    adx = ind.vadx(high, low, close)

    # 현재 값
    last_rsi = float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0
    last_close = float(close[-1])
    above20 = bool(last_close > sma20[-1]) if not np.isnan(sma20[-1]) else None
    above60 = bool(last_close > sma60[-1]) if not np.isnan(sma60[-1]) else None
    last_adx = float(adx[-1]) if not np.isnan(adx[-1]) else None

    # BB 위치
    bb_pos = None
    if not np.isnan(bb_upper[-1]) and not np.isnan(bb_lower[-1]):
        rng = bb_upper[-1] - bb_lower[-1]
        if rng > 0:
            bb_pos = round((last_close - bb_lower[-1]) / rng * 100, 1)

    # 점수 (-4 ~ +4)
    score = 0
    if last_rsi < 30:
        score += 2
    elif last_rsi < 40:
        score += 1
    elif last_rsi > 70:
        score -= 2
    elif last_rsi > 60:
        score -= 1
    if above20:
        score += 1
    elif above20 is not None:
        score -= 1
    if above60:
        score += 1
    elif above60 is not None:
        score -= 1

    if score >= 2:
        verdict = "강세"
    elif score <= -2:
        verdict = "약세"
    else:
        verdict = "중립"

    # 최근 20일 신호
    golden = sig.vgoldenCross(close, fast=20, slow=60)
    rsi_sig = sig.vrsiSignal(rsi)
    macd_sig = sig.vmacdSignal(close)
    recent = min(20, len(close))

    result = {
        "verdict": verdict,
        "score": score,
        "rsi": round(last_rsi, 1),
        "adx": round(last_adx, 1) if last_adx else None,
        "aboveSma20": above20,
        "aboveSma60": above60,
        "bbPosition": bb_pos,
        "signals": {
            "goldenCross": int(golden[-recent:].sum()),
            "rsiSignal": int(rsi_sig[-recent:].sum()),
            "macdSignal": int(macd_sig[-recent:].sum()),
        },
    }

    # 시장 대비 상대강도 + 베타 (가능하면)
    try:
        bench_result = _fetchBenchmark(
            benchmark or "KOSPI",
            stockCode=stockCode,
            market=market,
            benchmarkMode=benchmarkMode,
            returnMeta=True,
        )
        if isinstance(bench_result, tuple):
            marketDf, benchmark_meta = bench_result
        else:
            marketDf, benchmark_meta = bench_result, None
        if marketDf is not None and not marketDf.is_empty():
            rs = _relativeStrength(df, marketDf)
            beta = _calcBeta(df, marketDf)
            result["relativeStrength"] = rs
            result["beta"] = beta
            if benchmark_meta:
                result["benchmarkUsed"] = benchmark_meta
    except (ValueError, KeyError, AttributeError, ZeroDivisionError):
        pass

    # ── 카테고리 분해 (Phase 5 verdict 강화 + 12년 audit 검증) ──
    #
    # 12년 audit 결과 (5종목 2014~2026, Welch's t-test α=0.05):
    #   trend 강한상승: t=7.63@20d ✅ (12년 강건)
    #   trend 횡보:     t=-6.26@20d ✅ (12년 강건)
    #   trend 약한상승/약한하락: ❌ t 부족
    #   momentum 전부: ❌ 12년에서 모든 라벨 fail (5년 과적합)
    #   volatility 전부: ❌ 12년에서 모든 라벨 fail (5년 과적합)
    #   volume/pattern: ❌ 5년에서도 fail
    #
    # 결론: trend 만 유지, 2분류 (강한 상승 / 그 외)
    # momentum/volatility indicators 는 verdict dict 최상위에 이미 노출 (rsi/adx/bbPosition)
    result["categories"] = {
        "trend": _categoryTrend(close, high, low),
    }

    return result


# ── Audit 게이트 (Phase 5) ──────────────────────────────────────────────────


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

    Args:
        stockCodes: 종목 리스트 (예: KOSPI top 5)
        category: "trend"|"momentum"|"volatility"|"volume"|"pattern"
        horizons: forward return 측정 기간 (거래일)
        min_signals: 라벨당 최소 신호 수
        ratio_threshold: baseline 대비 수익률 비율 임계
        t_threshold: Welch's t-test 임계 (α=0.05 양측)

    Returns:
        {라벨명: {n_signals, avg_forward_5d, baseline_5d, ratio, t_stat, pass, horizon_details}}
    """
    import math

    from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays

    cat_fn = {
        "trend": _categoryTrend,
        "momentum": _categoryMomentum,
        "volatility": _categoryVolatility,
        "volume": _categoryVolume,
        "pattern": _categoryPattern,
    }[category]

    # 수집: 모든 종목 모든 시점의 (라벨, forward returns)
    label_returns: dict[str, dict[int, list[float]]] = {}  # {label: {horizon: [rets]}}
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
            # 카테고리 라벨 (t 시점까지의 데이터만 사용 — lookahead 방지)
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
                    # winsorize 1%/99%
                    label_returns[lbl][h].append(fwd)
                    baseline_returns[h].append(fwd)

    # Welch's t-test (scipy 0)
    def _welchT(a, b):
        na, nb = len(a), len(b)
        if na < 5 or nb < 5:
            return 0.0
        ma, mb = np.mean(a), np.mean(b)
        va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
        se = math.sqrt(va / na + vb / nb) if (va / na + vb / nb) > 0 else 1e-9
        return (ma - mb) / se

    # winsorize
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

        # 전체 pass = 하나 이상의 horizon 에서 pass
        lbl_result["pass"] = passes_any
        # 첫 horizon 의 상세를 최상위에도 복사 (편의)
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
    # 날짜 매칭 (str 변환)
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

    # 베타 t-stat: SE(β) = √(MSE / Σ(mr-x̄)²)
    n = len(sr)
    t_beta = None
    if n > 2 and var > 0:
        mse = ss_res / (n - 2)
        se_beta = np.sqrt(mse / var)
        if se_beta > 0:
            t_beta = float(beta / se_beta)

    # CAPM
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
