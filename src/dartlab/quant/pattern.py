"""캔들스틱 패턴 + 지지/저항 분석.

주요 캔들스틱 10종 패턴 인식 + zigzag 기반 지지/저항 수준.
"""

from __future__ import annotations

import numpy as np

from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays, resolve_market


def _cpDetect1DayPatterns(
    body: float,
    abs_body: float,
    upper_shadow: float,
    lower_shadow: float,
    body_ratio: float,
    date_str: str,
) -> dict | None:
    """1일 캔들 패턴 (Doji/Hammer/InvHammer/HangingMan/ShootingStar). 반환: dict or None."""
    if body_ratio < 0.1:
        return {"date": date_str, "pattern": "doji", "label": "도지", "signal": "반전 가능"}
    if lower_shadow >= abs_body * 2 and upper_shadow < abs_body * 0.5 and body > 0:
        return {"date": date_str, "pattern": "hammer", "label": "망치형", "signal": "상승 반전"}
    if upper_shadow >= abs_body * 2 and lower_shadow < abs_body * 0.5 and body > 0:
        return {"date": date_str, "pattern": "invertedHammer", "label": "역망치형", "signal": "상승 반전"}
    if lower_shadow >= abs_body * 2 and upper_shadow < abs_body * 0.5 and body < 0:
        return {"date": date_str, "pattern": "hangingMan", "label": "교수형", "signal": "하락 반전"}
    if upper_shadow >= abs_body * 2 and lower_shadow < abs_body * 0.5 and body < 0:
        return {"date": date_str, "pattern": "shootingStar", "label": "유성형", "signal": "하락 반전"}
    return None


def _cpDetect2DayPatterns(i: int, o, c, body: float, abs_body: float, date_str: str) -> list[dict]:
    """2일 패턴 (Engulfing / Piercing / DarkCloud)."""
    out: list[dict] = []
    prev_body = c[i - 1] - o[i - 1]
    abs_prev = abs(prev_body)
    if prev_body < 0 and body > 0 and abs_body > abs_prev and o[i] <= c[i - 1] and c[i] >= o[i - 1]:
        out.append({"date": date_str, "pattern": "bullishEngulfing", "label": "상승장악형", "signal": "상승 반전"})
    elif prev_body > 0 and body < 0 and abs_body > abs_prev and o[i] >= c[i - 1] and c[i] <= o[i - 1]:
        out.append({"date": date_str, "pattern": "bearishEngulfing", "label": "하락장악형", "signal": "하락 반전"})
    if prev_body < 0 and body > 0:
        mid = (o[i - 1] + c[i - 1]) / 2
        if o[i] < c[i - 1] and c[i] > mid and c[i] < o[i - 1]:
            out.append({"date": date_str, "pattern": "piercingLine", "label": "관통형", "signal": "상승 반전"})
    if prev_body > 0 and body < 0:
        mid = (o[i - 1] + c[i - 1]) / 2
        if o[i] > c[i - 1] and c[i] < mid and c[i] > o[i - 1]:
            out.append({"date": date_str, "pattern": "darkCloudCover", "label": "먹구름형", "signal": "하락 반전"})
    return out


def _cpDetect3DayPatterns(i: int, o, c, body: float, abs_body: float, full_range: float, date_str: str) -> dict | None:
    """3일 패턴 (Morning Star)."""
    prev2 = c[i - 2] - o[i - 2]
    prev1 = c[i - 1] - o[i - 1]
    if (
        prev2 < 0
        and abs(prev2) > full_range * 0.3
        and abs(prev1) < abs(prev2) * 0.3
        and body > 0
        and abs_body > abs(prev2) * 0.5
    ):
        return {"date": date_str, "pattern": "morningStar", "label": "샛별형", "signal": "상승 반전"}
    return None


def _cpScanPatterns(o, h, lo, c, dates, start: int, n: int) -> list[dict]:
    """start~n 범위 내 1/2/3일 패턴 전수 탐색."""
    patterns: list[dict] = []
    for i in range(start, n):
        body = c[i] - o[i]
        abs_body = abs(body)
        upper_shadow = h[i] - max(o[i], c[i])
        lower_shadow = min(o[i], c[i]) - lo[i]
        full_range = h[i] - lo[i]
        if full_range == 0:
            continue
        date_str = str(dates[i])[:10] if i < len(dates) else str(i)
        body_ratio = abs_body / full_range
        one = _cpDetect1DayPatterns(body, abs_body, upper_shadow, lower_shadow, body_ratio, date_str)
        if one:
            patterns.append(one)
        if i >= 1:
            patterns.extend(_cpDetect2DayPatterns(i, o, c, body, abs_body, date_str))
        if i >= 2:
            three = _cpDetect3DayPatterns(i, o, c, body, abs_body, full_range, date_str)
            if three:
                patterns.append(three)
    return patterns


def _cpSupportResistance(h, lo, c) -> dict:
    """지지/저항 zigzag pivot 분석. 반환: levels/current/nearest* dict."""
    pivots = _find_pivots(h, lo, threshold=0.05)
    if not pivots:
        return {}
    current_price = float(c[-1])
    supports = sorted(
        [p["price"] for p in pivots if p["type"] == "low" and p["price"] < current_price],
        reverse=True,
    )
    resistances = sorted([p["price"] for p in pivots if p["type"] == "high" and p["price"] > current_price])
    out: dict = {
        "supportLevels": [round(s, 2) for s in supports[:3]],
        "resistanceLevels": [round(r, 2) for r in resistances[:3]],
        "currentPrice": round(current_price, 2),
    }
    if supports:
        out["nearestSupport"] = round(supports[0], 2)
        out["supportDistance"] = round((current_price - supports[0]) / current_price * 100, 2)
    if resistances:
        out["nearestResistance"] = round(resistances[0], 2)
        out["resistanceDistance"] = round((resistances[0] - current_price) / current_price * 100, 2)
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
    ohlcv = fetch_ohlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcv_to_arrays(ohlcv)
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


def _find_pivots(high: np.ndarray, low: np.ndarray, threshold: float = 0.05) -> list[dict]:
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
