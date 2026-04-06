"""거시 차트 패턴 자동 인식 — W/M, H&S, 삼중바닥/천장, 원형천장/바닥.

캔들 9패턴(quant/pattern.py)이 단일 봉/2-3봉 단위라면,
이 모듈은 zigzag pivot 기반의 거시 패턴을 탐지한다.

각 패턴은 형성 시점, 신뢰도(0-1), 목표가(있으면)를 반환한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dartlab.quant._helpers import fetch_ohlcv, ohlcv_to_arrays, resolve_market
from dartlab.quant.pattern import _find_pivots


@dataclass(frozen=True)
class ChartPattern:
    """거시 차트 패턴 탐지 결과."""

    name: str  # "doubleBottom" | "doubleTop" | "headShoulders" | "invertedHS" | ...
    label: str  # 한글 라벨
    formedAt: str  # 패턴 완성 날짜 (YYYY-MM-DD)
    confidence: float  # 0.0-1.0
    targetPrice: float | None  # 목표가 (패턴 표준 공식)
    direction: str  # "bullish" | "bearish"
    description: str


# ══════════════════════════════════════
# 개별 패턴 탐지 함수
# ══════════════════════════════════════


def detectDoubleBottom(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """쌍바닥 W: 두 저점이 비슷, 사이 고점이 충분히 높음."""
    lows = [p for p in pivots if p["type"] == "low"]
    if len(lows) < 2:
        return None

    # 최근 두 저점
    l2, l1 = lows[-2], lows[-1]
    # 사이의 고점 찾기
    highs_between = [p for p in pivots if p["type"] == "high" and l2["idx"] < p["idx"] < l1["idx"]]
    if not highs_between:
        return None
    mid_high = max(highs_between, key=lambda p: p["price"])

    # 조건: 두 저점 차이 < 3%, 사이 고점 > 두 저점 +5%
    low_diff = abs(l1["price"] - l2["price"]) / l2["price"]
    rebound = (mid_high["price"] - max(l1["price"], l2["price"])) / max(l1["price"], l2["price"])
    if low_diff > 0.03 or rebound < 0.05:
        return None

    # 넥라인 돌파 확인 (현재가 > mid_high)
    if prices[-1] <= mid_high["price"]:
        return None

    confidence = max(0.5, 1.0 - low_diff * 10)  # 두 저점 일치할수록 높음
    target = mid_high["price"] + (mid_high["price"] - min(l1["price"], l2["price"]))  # 패턴 높이만큼

    return ChartPattern(
        name="doubleBottom",
        label="쌍바닥",
        formedAt=str(dates[l1["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bullish",
        description=f"쌍바닥 W형 — 두 저점({l2['price']:.0f}, {l1['price']:.0f}) + 넥라인 {mid_high['price']:.0f} 돌파",
    )


def detectDoubleTop(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """쌍봉 M: 두 고점이 비슷, 사이 저점이 충분히 낮음, 넥라인 하향 이탈."""
    highs = [p for p in pivots if p["type"] == "high"]
    if len(highs) < 2:
        return None

    h2, h1 = highs[-2], highs[-1]
    lows_between = [p for p in pivots if p["type"] == "low" and h2["idx"] < p["idx"] < h1["idx"]]
    if not lows_between:
        return None
    mid_low = min(lows_between, key=lambda p: p["price"])

    high_diff = abs(h1["price"] - h2["price"]) / h2["price"]
    drop = (min(h1["price"], h2["price"]) - mid_low["price"]) / min(h1["price"], h2["price"])
    if high_diff > 0.03 or drop < 0.05:
        return None

    if prices[-1] >= mid_low["price"]:
        return None

    confidence = max(0.5, 1.0 - high_diff * 10)
    target = mid_low["price"] - (max(h1["price"], h2["price"]) - mid_low["price"])

    return ChartPattern(
        name="doubleTop",
        label="쌍봉",
        formedAt=str(dates[h1["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bearish",
        description=f"쌍봉 M형 — 두 고점({h2['price']:.0f}, {h1['price']:.0f}) + 넥라인 {mid_low['price']:.0f} 이탈",
    )


def detectHeadShoulders(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """헤드앤숄더: 좌어깨 < 머리 > 우어깨, 어깨 비율 ±10%, 넥라인 수평."""
    highs = [p for p in pivots if p["type"] == "high"]
    if len(highs) < 3:
        return None

    ls, head, rs = highs[-3], highs[-2], highs[-1]
    # 머리가 가장 높아야 함
    if not (head["price"] > ls["price"] and head["price"] > rs["price"]):
        return None
    # 어깨 비율 ±10%
    shoulder_diff = abs(ls["price"] - rs["price"]) / ls["price"]
    if shoulder_diff > 0.10:
        return None

    # 어깨 사이 저점 (넥라인) 두 개 찾기
    lows = [p for p in pivots if p["type"] == "low"]
    necks = [p for p in lows if ls["idx"] < p["idx"] < rs["idx"]]
    if len(necks) < 2:
        return None
    n1, n2 = necks[0], necks[-1]
    neck_diff = abs(n1["price"] - n2["price"]) / n1["price"]
    if neck_diff > 0.05:  # 넥라인 거의 수평
        return None

    neckline = (n1["price"] + n2["price"]) / 2
    # 넥라인 하향 돌파 확인
    if prices[-1] >= neckline:
        return None

    confidence = max(0.5, 1.0 - shoulder_diff * 5 - neck_diff * 10)
    target = neckline - (head["price"] - neckline)  # 머리-넥라인 높이만큼 하락

    return ChartPattern(
        name="headShoulders",
        label="헤드앤숄더",
        formedAt=str(dates[rs["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bearish",
        description=f"H&S — 좌{ls['price']:.0f}/머리{head['price']:.0f}/우{rs['price']:.0f}, 넥라인 {neckline:.0f} 이탈",
    )


def detectInvertedHS(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """역H&S: H&S 거꾸로. 좌어깨 > 머리 < 우어깨, 넥라인 상향 돌파."""
    lows = [p for p in pivots if p["type"] == "low"]
    if len(lows) < 3:
        return None

    ls, head, rs = lows[-3], lows[-2], lows[-1]
    if not (head["price"] < ls["price"] and head["price"] < rs["price"]):
        return None
    shoulder_diff = abs(ls["price"] - rs["price"]) / ls["price"]
    if shoulder_diff > 0.10:
        return None

    highs = [p for p in pivots if p["type"] == "high"]
    necks = [p for p in highs if ls["idx"] < p["idx"] < rs["idx"]]
    if len(necks) < 2:
        return None
    n1, n2 = necks[0], necks[-1]
    neck_diff = abs(n1["price"] - n2["price"]) / n1["price"]
    if neck_diff > 0.05:
        return None

    neckline = (n1["price"] + n2["price"]) / 2
    if prices[-1] <= neckline:
        return None

    confidence = max(0.5, 1.0 - shoulder_diff * 5 - neck_diff * 10)
    target = neckline + (neckline - head["price"])

    return ChartPattern(
        name="invertedHS",
        label="역H&S",
        formedAt=str(dates[rs["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bullish",
        description=f"역H&S — 좌{ls['price']:.0f}/머리{head['price']:.0f}/우{rs['price']:.0f}, 넥라인 {neckline:.0f} 돌파",
    )


def detectTripleBottom(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """삼중바닥: 3개 저점이 비슷한 수준."""
    lows = [p for p in pivots if p["type"] == "low"]
    if len(lows) < 3:
        return None

    l3, l2, l1 = lows[-3], lows[-2], lows[-1]
    avg = (l1["price"] + l2["price"] + l3["price"]) / 3
    max_diff = max(abs(p["price"] - avg) / avg for p in (l1, l2, l3))
    if max_diff > 0.03:
        return None

    # 사이 고점들의 평균 = 저항선
    highs_between = [p for p in pivots if p["type"] == "high" and l3["idx"] < p["idx"] < l1["idx"]]
    if len(highs_between) < 2:
        return None
    resistance = sum(p["price"] for p in highs_between) / len(highs_between)
    if prices[-1] <= resistance:
        return None

    confidence = max(0.5, 1.0 - max_diff * 10)
    target = resistance + (resistance - avg)

    return ChartPattern(
        name="tripleBottom",
        label="삼중바닥",
        formedAt=str(dates[l1["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bullish",
        description=f"삼중바닥 — 3저점 평균 {avg:.0f}, 저항 {resistance:.0f} 돌파",
    )


def detectTripleTop(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """삼중천장: 3개 고점이 비슷한 수준."""
    highs = [p for p in pivots if p["type"] == "high"]
    if len(highs) < 3:
        return None

    h3, h2, h1 = highs[-3], highs[-2], highs[-1]
    avg = (h1["price"] + h2["price"] + h3["price"]) / 3
    max_diff = max(abs(p["price"] - avg) / avg for p in (h1, h2, h3))
    if max_diff > 0.03:
        return None

    lows_between = [p for p in pivots if p["type"] == "low" and h3["idx"] < p["idx"] < h1["idx"]]
    if len(lows_between) < 2:
        return None
    support = sum(p["price"] for p in lows_between) / len(lows_between)
    if prices[-1] >= support:
        return None

    confidence = max(0.5, 1.0 - max_diff * 10)
    target = support - (avg - support)

    return ChartPattern(
        name="tripleTop",
        label="삼중천장",
        formedAt=str(dates[h1["idx"]])[:10],
        confidence=round(confidence, 2),
        targetPrice=round(target, 2),
        direction="bearish",
        description=f"삼중천장 — 3고점 평균 {avg:.0f}, 지지 {support:.0f} 이탈",
    )


def detectRoundingBottom(prices: np.ndarray, dates: list, window: int = 60) -> ChartPattern | None:
    """원형바닥: 최근 window 구간에 2차 다항식 fit, 계수>0, R² 충분."""
    if len(prices) < window:
        return None

    y = prices[-window:]
    x = np.arange(window, dtype=float)
    # 2차 다항식 fit
    coeffs = np.polyfit(x, y, 2)
    a = coeffs[0]
    if a <= 0:  # 위로 볼록은 원형천장
        return None

    # R² 계산
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    if ss_tot == 0:
        return None
    r2 = 1 - ss_res / ss_tot
    if r2 < 0.7:
        return None

    # 현재가가 fit의 우상단 (회복) 지점이어야 함
    midpoint = y_pred[window // 2]
    if prices[-1] <= midpoint:
        return None

    return ChartPattern(
        name="roundingBottom",
        label="원형바닥",
        formedAt=str(dates[-1])[:10],
        confidence=round(min(1.0, r2), 2),
        targetPrice=None,  # 원형 패턴은 표준 목표가 공식 없음
        direction="bullish",
        description=f"원형바닥 — {window}일 2차 fit (a={a:.4f}, R²={r2:.2f}), 대전환 신호",
    )


def detectRoundingTop(prices: np.ndarray, dates: list, window: int = 60) -> ChartPattern | None:
    """원형천장: 2차 다항식 계수<0."""
    if len(prices) < window:
        return None

    y = prices[-window:]
    x = np.arange(window, dtype=float)
    coeffs = np.polyfit(x, y, 2)
    a = coeffs[0]
    if a >= 0:
        return None

    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    if ss_tot == 0:
        return None
    r2 = 1 - ss_res / ss_tot
    if r2 < 0.7:
        return None

    midpoint = y_pred[window // 2]
    if prices[-1] >= midpoint:
        return None

    return ChartPattern(
        name="roundingTop",
        label="원형천장",
        formedAt=str(dates[-1])[:10],
        confidence=round(min(1.0, r2), 2),
        targetPrice=None,
        direction="bearish",
        description=f"원형천장 — {window}일 2차 fit (a={a:.4f}, R²={r2:.2f}), 대전환 신호",
    )


# ══════════════════════════════════════
# 통합 진입점
# ══════════════════════════════════════


def detectChartPatterns(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    dates: list,
    pivot_threshold: float = 0.05,
) -> list[ChartPattern]:
    """모든 거시 차트 패턴을 한 번에 탐지.

    Args:
        high, low, close: OHLC numpy 배열
        dates: 날짜 리스트
        pivot_threshold: zigzag 임계값 (5%)

    Returns:
        탐지된 ChartPattern 리스트 (신뢰도 내림차순)
    """
    if len(close) < 30:
        return []

    pivots = _find_pivots(high, low, threshold=pivot_threshold)
    detected: list[ChartPattern] = []

    detectors = [
        lambda: detectDoubleBottom(pivots, close, dates),
        lambda: detectDoubleTop(pivots, close, dates),
        lambda: detectHeadShoulders(pivots, close, dates),
        lambda: detectInvertedHS(pivots, close, dates),
        lambda: detectTripleBottom(pivots, close, dates),
        lambda: detectTripleTop(pivots, close, dates),
        lambda: detectRoundingBottom(close, dates),
        lambda: detectRoundingTop(close, dates),
    ]

    for fn in detectors:
        try:
            result = fn()
            if result is not None:
                detected.append(result)
        except (ValueError, IndexError, ZeroDivisionError):
            continue

    detected.sort(key=lambda p: p.confidence, reverse=True)
    return detected


# ══════════════════════════════════════
# quant axis 진입점
# ══════════════════════════════════════


def analyze_chartPatterns(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """quant 축 진입점 — 거시 차트 패턴 자동 탐지.

    Args:
        stockCode: 종목코드 또는 ticker
        market: "KR" | "US" | "auto"

    Returns:
        dict with detected patterns + metadata
    """
    market = resolve_market(stockCode, market)
    ohlcv = fetch_ohlcv(stockCode, **kwargs)
    if ohlcv is None or ohlcv.is_empty():
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcv_to_arrays(ohlcv)
    h = arr.get("high")
    lo = arr.get("low")
    c = arr.get("close")
    dates = arr.get("date", [])

    if h is None or lo is None or c is None or len(c) < 30:
        return {"error": f"{stockCode} OHLC 데이터 부족 (30개 이상 필요)"}

    patterns = detectChartPatterns(h, lo, c, dates)

    return {
        "stockCode": stockCode,
        "market": market,
        "dataPoints": len(c),
        "patterns": [
            {
                "name": p.name,
                "label": p.label,
                "formedAt": p.formedAt,
                "confidence": p.confidence,
                "direction": p.direction,
                "targetPrice": p.targetPrice,
                "description": p.description,
            }
            for p in patterns
        ],
    }
