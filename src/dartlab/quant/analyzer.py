"""종합 기술적 분석 — 25개 지표 계산 + 판단(강세/중립/약세).

OHLCV DataFrame → 지표 DataFrame + 종합 판단 dict.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from dartlab.quant import indicators as ind
from dartlab.quant import signals as sig
from dartlab.core.polarsUtil import isEmptyDf


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


def technicalVerdict(df: pl.DataFrame) -> dict[str, Any]:
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
        market = _fetchBenchmark()
        if market is not None and not market.is_empty():
            rs = _relativeStrength(df, market)
            beta = _calcBeta(df, market)
            result["relativeStrength"] = rs
            result["beta"] = beta
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


# ── 5 카테고리 private 함수 (Phase 5 verdict 강화) ──────────────────────────


def _categoryTrend(close, high, low) -> dict:
    """추세 카테고리 — MA 정배열 + ADX + Supertrend + PSAR."""
    n = len(close)
    sma5 = ind.vsma(close, 5)
    sma20 = ind.vsma(close, 20)
    sma60 = ind.vsma(close, 60)
    sma120 = ind.vsma(close, 120)
    sma200 = ind.vsma(close, 200)
    adx = ind.vadx(high, low, close, 14)
    psar = ind.vpsar(high, low)
    st, st_dir = ind.vsupertrend(high, low, close)

    last = n - 1
    lc = float(close[last])

    # MA 정배열 점수 (-5 ~ +5): 인접 MA 쌍 비교
    mas = [sma5[last], sma20[last], sma60[last], sma120[last], sma200[last]]
    ma_score = 0
    for i in range(len(mas) - 1):
        if np.isnan(mas[i]) or np.isnan(mas[i + 1]):
            continue
        if mas[i] > mas[i + 1]:
            ma_score += 1
        else:
            ma_score -= 1
    ma_label = "정배열" if ma_score >= 3 else "역배열" if ma_score <= -3 else "혼조"

    # ADX 방향 기여
    last_adx = float(adx[last]) if not np.isnan(adx[last]) else 0
    adx_dir = 0.0
    if last_adx >= 25:
        adx_dir = 25.0 if lc > sma20[last] else -25.0
    elif last_adx >= 15:
        frac = (last_adx - 15) / 10
        adx_dir = frac * 25.0 * (1 if lc > sma20[last] else -1) if not np.isnan(sma20[last]) else 0

    # Supertrend / PSAR
    st_score = 12.5 if (not np.isnan(st_dir[last]) and st_dir[last] > 0) else -12.5
    psar_score = 12.5 if (not np.isnan(psar[last]) and lc > psar[last]) else -12.5

    raw = ma_score * 12.5 + adx_dir + st_score + psar_score
    score = float(np.clip(50 + raw / 2, 0, 100))

    # 2분류 (12년 audit: 강한상승 t=7.63 + 횡보 t=-6.26 만 pass. 나머지 fail → 병합)
    if score >= 70:
        label = "강한 상승"
    else:
        label = "횡보"

    return {
        "score": round(score, 1),
        "label": label,
        "indicators": {
            "ma_alignment": ma_label,
            "ma_alignment_score": ma_score,
            "adx": round(last_adx, 1),
            "adx_strong": last_adx >= 25,
            "supertrend": "long" if st_score > 0 else "short",
            "psar": "long" if psar_score > 0 else "short",
        },
    }


def _categoryMomentum(close, high, low) -> dict:
    """모멘텀 카테고리 — RSI + Stoch + MACD hist + CCI."""
    last = len(close) - 1
    rsi = ind.vrsi(close, 14)
    stoch_k, _ = ind.vstochastic(high, low, close)
    _, _, macd_hist = ind.vmacd(close)
    cci = ind.vcci(high, low, close, 20)

    def _safe(arr, idx):
        v = arr[idx] if idx < len(arr) else np.nan
        return float(v) if not np.isnan(v) else 50.0

    r = _safe(rsi, last)
    sk = _safe(stoch_k, last)
    mh = _safe(macd_hist, last)
    cc = _safe(cci, last)

    # 0~100 정규화
    r_norm = r  # RSI 는 이미 0~100
    sk_norm = sk  # Stoch 도 0~100
    mh_norm = 75.0 if mh > 0 else 25.0  # 방향만
    cc_norm = float(np.clip(50 + cc / 4, 0, 100))

    score = float(np.mean([r_norm, sk_norm, mh_norm, cc_norm]))

    # 3분류 (audit Phase C: 매도/강한매도 t<1.96 fail → 중립에 병합)
    labels = [(65, "강한 매수"), (50, "매수"), (0, "중립")]
    label = "중립"
    for thr, lbl in labels:
        if score >= thr:
            label = lbl
            break

    return {
        "score": round(score, 1),
        "label": label,
        "indicators": {
            "rsi": round(r, 1),
            "rsi_label": "과매수" if r >= 70 else "과매도" if r <= 30 else "중립",
            "stoch_k": round(sk, 1),
            "stoch_label": "과매수" if sk >= 80 else "과매도" if sk <= 20 else "중립",
            "macd_hist": round(mh, 4),
            "macd_label": "양전환" if mh > 0 else "음전환",
            "cci": round(cc, 1),
            "cci_label": "강세" if cc >= 100 else "약세" if cc <= -100 else "중립",
        },
    }


def _categoryVolatility(close, high, low) -> dict:
    """변동성 카테고리 — ATR%, BB%B, BB width percentile, Ulcer."""
    n = len(close)
    last = n - 1
    lc = float(close[last])

    atr = ind.vatr(high, low, close, 14)
    bb_up, bb_mid, bb_lo = ind.vbollinger(close, 20, 2.0)
    ulcer = ind.vulcer(close, 14)

    atr_pct = float(atr[last] / lc * 100) if not np.isnan(atr[last]) and lc > 0 else 0
    bb_range = bb_up[last] - bb_lo[last] if not np.isnan(bb_up[last]) and not np.isnan(bb_lo[last]) else 0
    bb_pctb = float((lc - bb_lo[last]) / bb_range * 100) if bb_range > 0 else 50
    bb_mid_val = bb_mid[last] if not np.isnan(bb_mid[last]) else lc
    bb_width_pct = float(bb_range / bb_mid_val * 100) if bb_mid_val > 0 else 0
    ulcer_val = float(ulcer[last]) if not np.isnan(ulcer[last]) else 0

    # BB width 60봉 percentile
    bb_widths = []
    for i in range(max(0, n - 60), n):
        r = bb_up[i] - bb_lo[i]
        m = bb_mid[i]
        if not np.isnan(r) and not np.isnan(m) and m > 0:
            bb_widths.append(r / m * 100)
    if bb_widths and len(bb_widths) >= 10:
        pct_rank = float(np.sum(np.array(bb_widths) <= bb_width_pct) / len(bb_widths) * 100)
    else:
        pct_rank = 50

    score = float(np.clip(100 - pct_rank, 0, 100))

    # 3분류 (audit Phase C: 급등가능/수축 fail → 확장/정상에 병합)
    labels = [(75, "극단 수축"), (40, "정상"), (0, "확장")]
    label = "확장"
    for thr, lbl in labels:
        if score >= thr:
            label = lbl
            break

    return {
        "score": round(score, 1),
        "label": label,
        "indicators": {
            "atr_pct": round(atr_pct, 2),
            "bb_percent_b": round(bb_pctb, 1),
            "bb_width_pct": round(bb_width_pct, 2),
            "bb_width_rank": round(pct_rank, 1),
            "ulcer": round(ulcer_val, 2),
        },
    }


def _categoryVolume(close, volume, high, low) -> dict:
    """거래량 카테고리 — OBV slope + MFI + OBV-price divergence."""
    n = len(close)
    last = n - 1

    obv = ind.vobv(close, volume)
    mfi = ind.vmfi(high, low, close, volume, 14)

    # OBV 5봉 slope (정규화)
    if n >= 6:
        obv_5 = obv[last - 4 : last + 1]
        obv_mean = float(np.mean(np.abs(obv_5))) if not np.any(np.isnan(obv_5)) else 1
        if obv_mean > 0 and not np.any(np.isnan(obv_5)):
            slope = float(np.polyfit(np.arange(5), obv_5, 1)[0]) / obv_mean
        else:
            slope = 0
    else:
        slope = 0

    obv_trend = "rising" if slope > 0.005 else "falling" if slope < -0.005 else "flat"
    obv_component = 75 if obv_trend == "rising" else 25 if obv_trend == "falling" else 50

    mfi_val = float(mfi[last]) if not np.isnan(mfi[last]) else 50
    mfi_label = "과매수" if mfi_val >= 80 else "과매도" if mfi_val <= 20 else "중립"

    # OBV-price divergence
    if n >= 6:
        price_5 = close[last - 4 : last + 1]
        price_slope = float(np.polyfit(np.arange(5), price_5, 1)[0]) if not np.any(np.isnan(price_5)) else 0
        divergence = (slope > 0.005 and price_slope < 0) or (slope < -0.005 and price_slope > 0)
    else:
        price_slope = 0
        divergence = False

    alignment = 75 if not divergence else 25
    score = float(np.mean([obv_component, mfi_val, alignment]))

    labels = [(75, "강한 매집"), (60, "매집"), (40, "중립"), (25, "분산"), (0, "강한 분산")]
    label = "강한 분산"
    for thr, lbl in labels:
        if score >= thr:
            label = lbl
            break

    return {
        "score": round(score, 1),
        "label": label,
        "indicators": {
            "obv_trend": obv_trend,
            "obv_5d_slope": round(slope * 100, 3),
            "mfi": round(mfi_val, 1),
            "mfi_label": mfi_label,
            "obv_price_divergence": divergence,
        },
    }


def _categoryPattern(df: pl.DataFrame) -> dict:
    """패턴 카테고리 — chartPatterns 8종 + 캔들스틱 (dead code 흡수)."""
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)
    open_ = df["open"].to_numpy().astype(np.float64) if "open" in df.columns else close

    # 차트 패턴 탐지 (chartPatterns.py 흡수)
    chart_pattern = "none"
    chart_direction = 0
    try:
        from dartlab.quant.chartPatterns import calcChartPatterns as _detect

        cp = _detect.__wrapped__(close, high, low) if hasattr(_detect, "__wrapped__") else None
        if cp is None:
            # 직접 호출 시도
            from dartlab.quant.chartPatterns import (
                detectDoubleBottom,
                detectDoubleTop,
                detectHeadShoulders,
            )

            for fn, name, d in [
                (detectDoubleBottom, "double_bottom", +1),
                (detectDoubleTop, "double_top", -1),
                (detectHeadShoulders, "head_shoulders", -1),
            ]:
                try:
                    r = fn(close, high, low)
                    if r and r.get("detected"):
                        chart_pattern = name
                        chart_direction = d
                        break
                except (TypeError, ValueError, IndexError):
                    continue
    except ImportError:
        pass

    # 캔들스틱 패턴 (pattern.py 흡수)
    candlestick_list = []
    try:
        from dartlab.quant.pattern import calcPattern as _candle

        cp_result = _candle.__wrapped__(close, high, low, open_) if hasattr(_candle, "__wrapped__") else None
        if cp_result is None:
            # 간단한 캔들 패턴 직접 감지
            if len(close) >= 2:
                body = close[-1] - open_[-1]
                total = high[-1] - low[-1]
                if total > 0 and abs(body) / total < 0.1:
                    candlestick_list.append("doji")
                elif body > 0 and (open_[-1] - low[-1]) > 2 * abs(body):
                    candlestick_list.append("hammer")
                elif body < 0 and (high[-1] - close[-1]) > 2 * abs(body):
                    candlestick_list.append("shooting_star")
        elif isinstance(cp_result, dict):
            candlestick_list = cp_result.get("candlesticks", [])
    except ImportError:
        pass

    candle_score = 0
    bullish_candles = {"hammer", "engulfing_bull", "morning_star", "piercing_line"}
    bearish_candles = {"shooting_star", "engulfing_bear", "evening_star", "dark_cloud"}
    for c in candlestick_list:
        if c in bullish_candles:
            candle_score += 10
        elif c in bearish_candles:
            candle_score -= 10

    # 지지 / 저항 (간단 — 최근 60봉 min/max)
    lookback = min(60, len(close))
    support = float(np.min(low[-lookback:]))
    resistance = float(np.max(high[-lookback:]))

    base = 50
    score = float(np.clip(base + chart_direction * 25 + candle_score, 0, 100))

    labels = [(65, "강세 패턴"), (35, "중립"), (0, "약세 패턴")]
    label = "약세 패턴"
    for thr, lbl in labels:
        if score >= thr:
            label = lbl
            break

    return {
        "score": round(score, 1),
        "label": label,
        "indicators": {
            "candlestick": candlestick_list[:5],
            "chart_pattern": chart_pattern,
            "support": round(support, 0),
            "resistance": round(resistance, 0),
        },
    }


# ── Audit 게이트 (Phase 5) ──────────────────────────────────────────────────


def _categoryEdgeAudit(
    stockCodes: list[str],
    category: str,
    *,
    horizons: tuple[int, ...] = (5, 10, 20),
    min_signals: int = 30,
    ratio_threshold: float = 1.3,
    t_threshold: float = 1.96,
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

    from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays

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
        ohlcv = fetch_ohlcv(code, start="2014-01-01")
        if isEmptyDf(ohlcv):
            continue
        arr = ohlcv_to_arrays(ohlcv)
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
    def _welch_t(a, b):
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
            t_stat = _welch_t(rets, base)

            passed = (
                n_sig >= min_signals
                and (abs(ratio) >= ratio_threshold or abs(ratio) <= 1 / ratio_threshold)
                and abs(t_stat) >= t_threshold
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


def _fetchBenchmark(benchmark: str = "KOSPI") -> pl.DataFrame | None:
    """시장 지수 OHLCV 수집."""
    from dartlab.gather.entry import _INDEX_SYMBOLS, _fetchNaverIndex

    sym = _INDEX_SYMBOLS.get(benchmark, benchmark)
    df = _fetchNaverIndex(sym, 300)
    return df if not df.is_empty() else None


def _relativeStrength(stock_df: pl.DataFrame, market_df: pl.DataFrame) -> float | None:
    """종목 RSI - 시장 RSI → 상대강도."""
    s_close = stock_df["close"].to_numpy().astype(np.float64)
    m_close = market_df["close"].to_numpy().astype(np.float64)

    s_rsi = ind.vrsi(s_close, 14)
    m_rsi = ind.vrsi(m_close, 14)

    last_s = float(s_rsi[-1]) if not np.isnan(s_rsi[-1]) else None
    last_m = float(m_rsi[-1]) if not np.isnan(m_rsi[-1]) else None

    if last_s is not None and last_m is not None:
        return round(last_s - last_m, 1)
    return None


def _calcBeta(stock_df: pl.DataFrame, market_df: pl.DataFrame) -> dict | None:
    """종목 vs 시장 OLS 베타 + CAPM."""
    # 날짜 매칭 (str 변환)
    s_dates = set(str(d) for d in stock_df["date"].to_list())
    m_dates = set(str(d) for d in market_df["date"].to_list())
    common = sorted(s_dates & m_dates)

    if len(common) < 30:
        return None

    s_df = stock_df.with_columns(pl.col("date").cast(pl.Utf8).alias("_d")).filter(pl.col("_d").is_in(common)).sort("_d")
    m_df = (
        market_df.with_columns(pl.col("date").cast(pl.Utf8).alias("_d")).filter(pl.col("_d").is_in(common)).sort("_d")
    )

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
        "value": round(beta, 3),
        "alpha": round(alpha * 252 * 100, 2),
        "rSquared": round(r_sq, 4),
        "tStat": round(t_beta, 2) if t_beta is not None else None,
        "nObs": len(sr),
        "capm": capm,
    }
