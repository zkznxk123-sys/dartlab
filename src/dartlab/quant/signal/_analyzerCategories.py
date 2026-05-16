"""quant/signal/analyzer 5 카테고리 헬퍼 — trend/momentum/volatility/volume/pattern.

quant/signal/analyzer.py 가 818 줄 god module 이라 5 카테고리 함수를 분리.
identity 보존을 위해 analyzer.py 가 본 모듈에서 re-export 한다.

함수:
- _categoryTrend — MA 정배열 + ADX + Supertrend + PSAR
- _categoryMomentum — RSI + Stoch + MACD hist + CCI
- _categoryVolatility — ATR% + BB%B + BB width percentile + Ulcer
- _categoryVolume — OBV slope + MFI + divergence
- _categoryPattern — chartPatterns 8종 + 캔들스틱
"""

from __future__ import annotations

import numpy as np
import polars as pl

from dartlab.synth import indicators as ind


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

    last_adx = float(adx[last]) if not np.isnan(adx[last]) else 0
    adx_dir = 0.0
    if last_adx >= 25:
        adx_dir = 25.0 if lc > sma20[last] else -25.0
    elif last_adx >= 15:
        frac = (last_adx - 15) / 10
        adx_dir = frac * 25.0 * (1 if lc > sma20[last] else -1) if not np.isnan(sma20[last]) else 0

    st_score = 12.5 if (not np.isnan(st_dir[last]) and st_dir[last] > 0) else -12.5
    psar_score = 12.5 if (not np.isnan(psar[last]) and lc > psar[last]) else -12.5

    raw = ma_score * 12.5 + adx_dir + st_score + psar_score
    score = float(np.clip(50 + raw / 2, 0, 100))

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

    r_norm = r
    sk_norm = sk
    mh_norm = 75.0 if mh > 0 else 25.0
    cc_norm = float(np.clip(50 + cc / 4, 0, 100))

    score = float(np.mean([r_norm, sk_norm, mh_norm, cc_norm]))

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
    """패턴 카테고리 — chartPatterns 8종 + 캔들스틱."""
    close = df["close"].to_numpy().astype(np.float64)
    high = df["high"].to_numpy().astype(np.float64)
    low = df["low"].to_numpy().astype(np.float64)
    open_ = df["open"].to_numpy().astype(np.float64) if "open" in df.columns else close

    chart_pattern = "none"
    chart_direction = 0
    try:
        from dartlab.quant.regime.chartPatterns import calcChartPatterns as _detect

        cp = _detect.__wrapped__(close, high, low) if hasattr(_detect, "__wrapped__") else None
        if cp is None:
            from dartlab.quant.regime.chartPatterns import (
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

    candlestick_list: list[str] = []
    try:
        from dartlab.quant.regime.pattern import calcPattern as _candle

        cp_result = _candle.__wrapped__(close, high, low, open_) if hasattr(_candle, "__wrapped__") else None
        if cp_result is None:
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


__all__ = [
    "_categoryMomentum",
    "_categoryPattern",
    "_categoryTrend",
    "_categoryVolatility",
    "_categoryVolume",
]
