"""모멘텀 분석 — 횡단면/시계열/52주 신고가.

학술 근거:
- Jegadeesh & Titman (1993): 12-1개월 횡단면 모멘텀
- Moskowitz, Ooi, Pedersen (2012): 시계열 모멘텀 (TSMOM)
- George & Hwang (2004): 52주 신고가 비율
- Barroso & Santa-Clara (2015): 모멘텀 크래시 리스크 헤징
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


def _momentumSeries(close: np.ndarray) -> dict:
    """시계열 모멘텀 계산 — Strategy DSL 입력용 (rolling)."""
    n = len(close)
    out = {
        "ts12_1": np.full(n, np.nan, dtype=np.float64),
        "ts6_1": np.full(n, np.nan, dtype=np.float64),
        "ts_high52": np.full(n, np.nan, dtype=np.float64),
    }
    for i in range(252, n):
        out["ts12_1"][i] = close[i - 22] / close[i - 252] - 1
    for i in range(126, n):
        out["ts6_1"][i] = close[i - 22] / close[i - 126] - 1
    for i in range(252, n):
        h52 = float(np.max(close[i - 252 : i + 1]))
        out["ts_high52"][i] = close[i] / h52 if h52 > 0 else np.nan
    return out


def calcMomentum(stockCode: str, *, market: str = "auto", series: bool = False, **kwargs) -> dict:
    """모멘텀 종합 분석 — Jegadeesh-Titman + Moskowitz TS + 52w-high.

    Capabilities:
        12-1 m 횡단면 모멘텀 (Jegadeesh-Titman 1993, 최근 1m skip 으로
        short-term reversal 제거) + 시계열 모멘텀 (Moskowitz et al. 2012,
        과거 12m 부호 지속) + 52주 신고가 대비 비율 (George-Hwang 2004) +
        crash risk (skewness 기반). 데이터 252 일 미만 시 6-1 m 폴백.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".
        series: True 면 ``_series`` (ts12_1, ts6_1, ts_high52 NDArray) 추가.

    Returns:
        dict:
            - ``momentum12_1`` (float): 12-1 m return (최근 1m 제외).
            - ``return12m``/``return1m`` (float): 단순 12m/1m 수익률.
            - ``tsMomentum`` (str): "up"|"down"|"flat".
            - ``highRatio52w`` (float): 현재 / 52주 신고가 비율.
            - ``crashRisk`` (float): 음의 skewness (가까울수록 폭락 위험).
            - 또는 ``error`` (str): 22 일 미만.

    Raises:
        없음 (error 키).

    Example:
        >>> r = calcMomentum("005930")
        >>> r["momentum12_1"], r["highRatio52w"]
        (0.15, 0.92)  # 12-1 m +15%, 52w 신고가 92%

    Guide:
        - momentum12_1 ≥ 20% + highRatio52w ≥ 95% = 강한 모멘텀 (성장주).
        - 음의 모멘텀 (< -10%) + crashRisk 큼 = 회복 전 추가 하락 위험.
        - 22 일 미만 = error, 252 일 미만 = 6-1 m 폴백, ≥ 252 일 = 12-1 m.

    SeeAlso:
        - ``calcVolume``: 거래량 흐름
        - ``calcVolatility``: vol regime (모멘텀 회사는 vol 도 큼)
        - ``synth.indicators.momentum``: RSI/MACD

    Requires:
        OHLCV 일별 ≥ 22 일 (12-1 m 완전 신호는 ≥ 252 일).

    AIContext:
        12-1 m 단독 인용 금지 — highRatio52w + crashRisk 함께. 252 일 미만은
        6-1 m 폴백 사용 명시. KR 회사 모멘텀 사이클은 US 대비 짧음 (3~6m).

    LLM Specifications:
        AntiPatterns:
            - 최근 1m 포함 단순 12m 인용 — short-term reversal 노이즈.
            - 252 일 미만에 12-1 m 단정 — 본 함수가 None 반환.
        OutputSchema:
            ``{momentum12_1: float, return12m, return1m, tsMomentum: str,
              highRatio52w: float, crashRisk: float}``.
        Prerequisites:
            OHLCV ≥ 22 일 (≥ 252 일 권장).
        Freshness:
            일별.
        Dataflow:
            OHLCV → close → 12-1 m + 6-1 m + TS + 52w high + skewness.
        TargetMarkets: KR (KRX), US (NYSE/NASDAQ).
    """
    market = resolveMarket(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
    if "close" not in arr or len(arr["close"]) < 22:
        return {"error": f"{stockCode} 데이터 부족 (최소 22일 필요)"}

    close = arr["close"]
    n = len(close)

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "dataPoints": n,
    }
    if series:
        result["_series"] = _momentumSeries(close)

    # ── 12-1개월 횡단면 모멘텀 (Jegadeesh-Titman) ──
    # 최근 1개월 제외, 그 이전 11개월 수익률
    if n >= 252:
        ret_12m = close[-22] / close[-252] - 1  # 12개월 수익률
        ret_1m = close[-1] / close[-22] - 1  # 최근 1개월 수익률
        mom_12_1 = close[-22] / close[-252] - 1  # skip most recent month
        result["momentum12_1"] = round(float(mom_12_1), 4)
        result["return12m"] = round(float(ret_12m), 4)
        result["return1m"] = round(float(ret_1m), 4)
    elif n >= 126:
        ret_6m = close[-22] / close[-126] - 1
        result["momentum6_1"] = round(float(ret_6m), 4)
        result["momentum12_1"] = None
    else:
        result["momentum12_1"] = None

    # ── 시계열 모멘텀 (Moskowitz et al. 2012) ──
    # 과거 12개월 자신의 수익률 부호 → 같은 방향 지속 여부
    ts_signals = {}
    for label, lookback in [("1m", 22), ("3m", 63), ("6m", 126), ("12m", 252)]:
        if n > lookback:
            ret = close[-1] / close[-lookback] - 1
            ts_signals[label] = {
                "return": round(float(ret), 4),
                "signal": "long" if ret > 0 else "short",
            }
    result["tsMomentum"] = ts_signals

    # ── 52주 신고가 비율 (George & Hwang 2004) ──
    if n >= 252:
        high_52w = float(np.max(arr.get("high", close)[-252:]))
        current = float(close[-1])
        ratio = current / high_52w if high_52w > 0 else 0
        result["highRatio52w"] = round(ratio, 4)
        result["high52w"] = round(high_52w, 2)
        # 해석: 0.95+ = 신고가 근접, 0.7- = 크게 하락
        if ratio >= 0.95:
            result["highProximity"] = "신고가 근접"
        elif ratio >= 0.80:
            result["highProximity"] = "상위권"
        elif ratio >= 0.60:
            result["highProximity"] = "중간"
        else:
            result["highProximity"] = "하위권"
    else:
        result["highRatio52w"] = None

    # ── 모멘텀 크래시 리스크 (Barroso & Santa-Clara 2015) ──
    # 최근 실현변동성이 높으면 모멘텀 크래시 위험 증가
    if n >= 126:
        daily_returns = np.diff(np.log(close[-126:]))
        realizedVol = float(np.std(daily_returns) * np.sqrt(252))
        # 변동성 상위 구간이면 모멘텀 위험
        if realizedVol > 0.5:
            crash_risk = "high"
        elif realizedVol > 0.3:
            crash_risk = "medium"
        else:
            crash_risk = "low"
        result["crashRisk"] = crash_risk
        result["realizedVol6m"] = round(realizedVol, 4)
    else:
        result["crashRisk"] = None

    # ── 모멘텀 연속성 (streak) ──
    if n >= 22:
        monthly_returns = []
        for i in range(min(12, n // 22)):
            start_idx = -(i + 1) * 22
            end_idx = -i * 22 if i > 0 else None
            if abs(start_idx) <= n:
                if end_idx is None:
                    mr = close[-1] / close[start_idx] - 1
                else:
                    mr = close[end_idx] / close[start_idx] - 1
                monthly_returns.append(mr)

        if monthly_returns:
            # 최근 연속 양(+)/음(-) 개월 수
            streak = 0
            direction = 1 if monthly_returns[0] > 0 else -1
            for mr in monthly_returns:
                if (mr > 0 and direction > 0) or (mr <= 0 and direction <= 0):
                    streak += 1
                else:
                    break
            result["streak"] = streak * direction
            result["streakDirection"] = "상승" if direction > 0 else "하락"

    # ── 종합 판단 ──
    signals_count = sum(1 for v in ts_signals.values() if isinstance(v, dict) and v.get("signal") == "long")
    total_signals = len(ts_signals)
    if total_signals > 0:
        if signals_count == total_signals:
            result["momentumVerdict"] = "strong_bullish"
        elif signals_count >= total_signals * 0.75:
            result["momentumVerdict"] = "bullish"
        elif signals_count >= total_signals * 0.5:
            result["momentumVerdict"] = "mixed"
        elif signals_count > 0:
            result["momentumVerdict"] = "bearish"
        else:
            result["momentumVerdict"] = "strong_bearish"

    return result
