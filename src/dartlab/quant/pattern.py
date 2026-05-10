"""캔들스틱 패턴 + 지지/저항 분석.

주요 캔들스틱 10종 패턴 인식 + zigzag 기반 지지/저항 수준.
"""

from __future__ import annotations

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant._helpers import fetchOhlcv, ohlcvToArrays, resolve_market


def _cpDetect1DayPatterns(
    body: float,
    absBody: float,
    upperShadow: float,
    lowerShadow: float,
    bodyRatio: float,
    dateStr: str,
) -> dict | None:
    """1일 캔들 패턴 (Doji/Hammer/InvHammer/HangingMan/ShootingStar). 반환: dict or None."""
    if bodyRatio < 0.1:
        return {"date": dateStr, "pattern": "doji", "label": "도지", "signal": "반전 가능"}
    if lowerShadow >= absBody * 2 and upperShadow < absBody * 0.5 and body > 0:
        return {"date": dateStr, "pattern": "hammer", "label": "망치형", "signal": "상승 반전"}
    if upperShadow >= absBody * 2 and lowerShadow < absBody * 0.5 and body > 0:
        return {"date": dateStr, "pattern": "invertedHammer", "label": "역망치형", "signal": "상승 반전"}
    if lowerShadow >= absBody * 2 and upperShadow < absBody * 0.5 and body < 0:
        return {"date": dateStr, "pattern": "hangingMan", "label": "교수형", "signal": "하락 반전"}
    if upperShadow >= absBody * 2 and lowerShadow < absBody * 0.5 and body < 0:
        return {"date": dateStr, "pattern": "shootingStar", "label": "유성형", "signal": "하락 반전"}
    return None


def _cpDetect2DayPatterns(i: int, o, c, body: float, absBody: float, dateStr: str) -> list[dict]:
    """2일 패턴 (Engulfing / Piercing / DarkCloud)."""
    out: list[dict] = []
    prev_body = c[i - 1] - o[i - 1]
    abs_prev = abs(prev_body)
    if prev_body < 0 and body > 0 and absBody > abs_prev and o[i] <= c[i - 1] and c[i] >= o[i - 1]:
        out.append({"date": dateStr, "pattern": "bullishEngulfing", "label": "상승장악형", "signal": "상승 반전"})
    elif prev_body > 0 and body < 0 and absBody > abs_prev and o[i] >= c[i - 1] and c[i] <= o[i - 1]:
        out.append({"date": dateStr, "pattern": "bearishEngulfing", "label": "하락장악형", "signal": "하락 반전"})
    if prev_body < 0 and body > 0:
        mid = (o[i - 1] + c[i - 1]) / 2
        if o[i] < c[i - 1] and c[i] > mid and c[i] < o[i - 1]:
            out.append({"date": dateStr, "pattern": "piercingLine", "label": "관통형", "signal": "상승 반전"})
    if prev_body > 0 and body < 0:
        mid = (o[i - 1] + c[i - 1]) / 2
        if o[i] > c[i - 1] and c[i] < mid and c[i] > o[i - 1]:
            out.append({"date": dateStr, "pattern": "darkCloudCover", "label": "먹구름형", "signal": "하락 반전"})
    return out


def _cpDetect3DayPatterns(i: int, o, c, body: float, absBody: float, fullRange: float, dateStr: str) -> dict | None:
    """3일 패턴 (Morning Star)."""
    prev2 = c[i - 2] - o[i - 2]
    prev1 = c[i - 1] - o[i - 1]
    if (
        prev2 < 0
        and abs(prev2) > fullRange * 0.3
        and abs(prev1) < abs(prev2) * 0.3
        and body > 0
        and absBody > abs(prev2) * 0.5
    ):
        return {"date": dateStr, "pattern": "morningStar", "label": "샛별형", "signal": "상승 반전"}
    return None


def _cpScanPatterns(o, h, lo, c, dates, start: int, n: int) -> list[dict]:
    """start~n 범위 내 1/2/3일 패턴 전수 탐색."""
    patterns: list[dict] = []
    for i in range(start, n):
        body = c[i] - o[i]
        absBody = abs(body)
        upperShadow = h[i] - max(o[i], c[i])
        lowerShadow = min(o[i], c[i]) - lo[i]
        fullRange = h[i] - lo[i]
        if fullRange == 0:
            continue
        dateStr = str(dates[i])[:10] if i < len(dates) else str(i)
        bodyRatio = absBody / fullRange
        one = _cpDetect1DayPatterns(body, absBody, upperShadow, lowerShadow, bodyRatio, dateStr)
        if one:
            patterns.append(one)
        if i >= 1:
            patterns.extend(_cpDetect2DayPatterns(i, o, c, body, absBody, dateStr))
        if i >= 2:
            three = _cpDetect3DayPatterns(i, o, c, body, absBody, fullRange, dateStr)
            if three:
                patterns.append(three)
    return patterns


def _cpSupportResistance(h, lo, c) -> dict:
    """지지/저항 zigzag pivot 분석. 반환: levels/current/nearest* dict."""
    pivots = _findPivots(h, lo, threshold=0.05)
    if not pivots:
        return {}
    currentPrice = float(c[-1])
    supports = sorted(
        [p["price"] for p in pivots if p["type"] == "low" and p["price"] < currentPrice],
        reverse=True,
    )
    resistances = sorted([p["price"] for p in pivots if p["type"] == "high" and p["price"] > currentPrice])
    out: dict = {
        "supportLevels": [round(s, 2) for s in supports[:3]],
        "resistanceLevels": [round(r, 2) for r in resistances[:3]],
        "currentPrice": round(currentPrice, 2),
    }
    if supports:
        out["nearestSupport"] = round(supports[0], 2)
        out["supportDistance"] = round((currentPrice - supports[0]) / currentPrice * 100, 2)
    if resistances:
        out["nearestResistance"] = round(resistances[0], 2)
        out["resistanceDistance"] = round((resistances[0] - currentPrice) / currentPrice * 100, 2)
    return out


def _cpVerdict(patterns: list[dict]) -> str:
    """최근 5 패턴의 방향 합산 판정 — bullish/bearish/neutral/no_pattern."""
    if not patterns:
        return "no_pattern"
    recent = patterns[-5:]
    bullish = sum(1 for p in recent if "상승" in p.get("signal", ""))
    bearish = sum(1 for p in recent if "하락" in p.get("signal", ""))
    if bullish > bearish:
        return "bullish"
    if bearish > bullish:
        return "bearish"
    return "neutral"


def calcPattern(stockCode: str, *, market: str = "auto", lookback: int = 20, **kwargs) -> dict:
    """캔들스틱 패턴 + 지지/저항 분석 orchestrator (Q3.1f split).

    Parameters
    ----------
    stockCode : str
        종목코드 또는 ticker.
    market : str
        "KR" | "US" | "auto".
    lookback : int
        패턴 탐색 기간 (일).

    Returns
    -------
    dict
        stockCode : str — 입력 종목
        market : str — resolved market
        dataPoints : int — OHLCV 길이
        patterns : list[dict] — 최근 10 패턴 (date/pattern/label/signal)
        patternCount : int — 전체 감지 수
        supportLevels, resistanceLevels : list[float] — 상위 3개
        currentPrice : float — 최신 종가
        nearestSupport, supportDistance : float — 가장 가까운 지지 + 거리 (%)
        nearestResistance, resistanceDistance : float — 저항
        patternVerdict : str — "bullish"/"bearish"/"neutral"/"no_pattern"
    """
    market = resolve_market(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
    o = arr.get("open")
    h = arr.get("high")
    lo = arr.get("low")
    c = arr.get("close")
    dates = arr.get("date", [])

    if o is None or h is None or lo is None or c is None or len(c) < 5:
        return {"error": f"{stockCode} OHLC 데이터 부족"}

    n = len(c)
    result: dict = {"stockCode": stockCode, "market": market, "dataPoints": n}

    patterns = _cpScanPatterns(o, h, lo, c, dates, max(2, n - lookback), n)
    result["patterns"] = patterns[-10:]
    result["patternCount"] = len(patterns)
    result.update(_cpSupportResistance(h, lo, c))
    result["patternVerdict"] = _cpVerdict(patterns)

    return result


def _findPivots(high: np.ndarray, low: np.ndarray, threshold: float = 0.05) -> list[dict]:
    """간이 zigzag로 pivot points 탐색.

    Args:
        high: 고가 배열.
        low: 저가 배열.
        threshold: 전환 판단 임계값 (5%).

    Returns:
        list of {"idx", "price", "type": "high"|"low"}
    """
    n = len(high)
    if n < 5:
        return []

    pivots = []
    # 초기 방향
    direction = 1  # 1 = 상승 탐색, -1 = 하락 탐색
    last_high_idx = 0
    last_low_idx = 0
    last_high = float(high[0])
    last_low = float(low[0])

    for i in range(1, n):
        h_val = float(high[i])
        l_val = float(low[i])

        if direction == 1:
            if h_val > last_high:
                last_high = h_val
                last_high_idx = i
            elif last_high > 0 and (last_high - l_val) / last_high >= threshold:
                pivots.append({"idx": last_high_idx, "price": last_high, "type": "high"})
                direction = -1
                last_low = l_val
                last_low_idx = i
        else:
            if l_val < last_low:
                last_low = l_val
                last_low_idx = i
            elif last_low > 0 and (h_val - last_low) / last_low >= threshold:
                pivots.append({"idx": last_low_idx, "price": last_low, "type": "low"})
                direction = 1
                last_high = h_val
                last_high_idx = i

    return pivots
