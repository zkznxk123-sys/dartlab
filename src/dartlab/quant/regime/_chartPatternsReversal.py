"""차트 패턴 — Double + Head&Shoulders 4 함수 (반전형 1)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChartPattern:
    """거시 차트 패턴 탐지 결과."""

    name: str
    label: str
    formedAt: str
    confidence: float
    targetPrice: float | None
    direction: str
    description: str


def detectDoubleBottom(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """쌍바닥 W: 두 저점이 비슷, 사이 고점이 충분히 높음.

    Capabilities:
        - 최근 두 저점의 가격 차이가 3% 이내 + 사이 고점이 5% 이상 반등 + 현재가가 넥라인 돌파 시 W 패턴 탐지
        - 두 저점 일치도 기반 confidence + 패턴 높이만큼 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과. 각 dict 에 ``type/idx/price`` 키.
        prices: 종가 배열 (넥라인 돌파 확인용).
        dates: 날짜 리스트 (formedAt 산출).

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bullish"``, 미탐지 시 None.

    Guide:
        반전형 패턴 — 하락 추세 종료 후 첫 매수 시그널. confidence ≥ 0.7 권장.
        목표가 = 넥라인 + (넥라인 - 저점) 패턴 표준 공식.

    When:
        Quant regime 패턴 축 평가 + AI 상승 반전 탐지 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출 → 결과를 detected 리스트에 누적.

    Requires:
        pivots ≥ 2 low + close 시계열 ≥ 30 일.

    Raises:
        없음 — 조건 미충족 시 None.

    Example:
        >>> p = detectDoubleBottom(pivots, close, dates)
        >>> p.direction if p else None
        'bullish'

    See Also:
        - detectDoubleTop : 대칭 bearish 패턴
        - detectChartPatterns : 통합 진입점
        - calcChartPatterns : quant 축 진입점

    AIContext:
        쌍바닥 W 탐지 시 ``confidence`` + ``targetPrice`` 인용 → "넥라인 X 돌파, 목표 Y" 답변.
    """
    lows = [p for p in pivots if p["type"] == "low"]
    if len(lows) < 2:
        return None

    l2, l1 = lows[-2], lows[-1]
    highs_between = [p for p in pivots if p["type"] == "high" and l2["idx"] < p["idx"] < l1["idx"]]
    if not highs_between:
        return None
    mid_high = max(highs_between, key=lambda p: p["price"])

    low_diff = abs(l1["price"] - l2["price"]) / l2["price"]
    rebound = (mid_high["price"] - max(l1["price"], l2["price"])) / max(l1["price"], l2["price"])
    if low_diff > 0.03 or rebound < 0.05:
        return None

    if prices[-1] <= mid_high["price"]:
        return None

    confidence = max(0.5, 1.0 - low_diff * 10)
    target = mid_high["price"] + (mid_high["price"] - min(l1["price"], l2["price"]))

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
    """쌍봉 M: 두 고점이 비슷, 사이 저점이 충분히 낮음, 넥라인 하향 이탈.

    Capabilities:
        - 최근 두 고점의 가격 차이가 3% 이내 + 사이 저점이 5% 이상 하락 + 현재가가 넥라인 하향 이탈 시 M 패턴 탐지
        - 두 고점 일치도 기반 confidence + 패턴 높이만큼 하락 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과.
        prices: 종가 배열.
        dates: 날짜 리스트.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bearish"``.

    Guide:
        반전형 패턴 — 상승 추세 종료 후 첫 매도 시그널. confidence ≥ 0.7 권장.

    When:
        Quant regime 패턴 축 + AI 하락 반전 경고 답변.

    How:
        ``detectChartPatterns`` 에서 detectDoubleBottom 직후 호출.

    Requires:
        pivots ≥ 2 high + close 시계열 ≥ 30 일.

    Raises:
        없음.

    Example:
        >>> p = detectDoubleTop(pivots, close, dates)
        >>> p.direction if p else None
        'bearish'

    See Also:
        - detectDoubleBottom : 대칭 bullish
        - detectChartPatterns : 통합 진입점

    AIContext:
        쌍봉 M 탐지 시 매도 시그널로 ``targetPrice`` 까지 하락 가능성 답변.
    """
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
    """헤드앤숄더: 좌어깨 < 머리 > 우어깨, 어깨 비율 ±10%, 넥라인 수평.

    Capabilities:
        - 좌·우 어깨 ±10% 일치 + 머리 최고점 + 넥라인 두 저점 ±5% + 현재가 넥라인 하향 돌파 시 탐지
        - 머리·넥라인 폭만큼 하락 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과.
        prices: 종가 배열.
        dates: 날짜 리스트.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bearish"``.

    Guide:
        고전적 반전 패턴 — 상승 추세 종료 강력 시그널. 어깨 비율과 넥라인 수평성으로 confidence 가중.

    When:
        Quant regime + AI 추세 반전 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        highs ≥ 3 + lows ≥ 2.

    Raises:
        없음.

    Example:
        >>> p = detectHeadShoulders(pivots, close, dates)
        >>> p.targetPrice if p else None
        24800.0

    See Also:
        - detectInvertedHS : 대칭 bullish
        - detectChartPatterns : 통합 진입점

    AIContext:
        H&S 탐지 시 ``description`` 의 좌/머리/우 가격 + 넥라인 인용 → 신뢰도 높은 매도 신호 답변.
    """
    highs = [p for p in pivots if p["type"] == "high"]
    if len(highs) < 3:
        return None

    ls, head, rs = highs[-3], highs[-2], highs[-1]
    if not (head["price"] > ls["price"] and head["price"] > rs["price"]):
        return None
    shoulder_diff = abs(ls["price"] - rs["price"]) / ls["price"]
    if shoulder_diff > 0.10:
        return None

    lows = [p for p in pivots if p["type"] == "low"]
    necks = [p for p in lows if ls["idx"] < p["idx"] < rs["idx"]]
    if len(necks) < 2:
        return None
    n1, n2 = necks[0], necks[-1]
    neck_diff = abs(n1["price"] - n2["price"]) / n1["price"]
    if neck_diff > 0.05:
        return None

    neckline = (n1["price"] + n2["price"]) / 2
    if prices[-1] >= neckline:
        return None

    confidence = max(0.5, 1.0 - shoulder_diff * 5 - neck_diff * 10)
    target = neckline - (head["price"] - neckline)

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
    """역H&S: H&S 거꾸로. 좌어깨 > 머리 < 우어깨, 넥라인 상향 돌파.

    Capabilities:
        - 좌·우 어깨 ±10% 일치 + 머리 최저점 + 넥라인 두 고점 ±5% + 현재가 넥라인 상향 돌파 시 탐지
        - 머리·넥라인 폭만큼 상승 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과.
        prices: 종가 배열.
        dates: 날짜 리스트.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bullish"``.

    Guide:
        고전적 반전 패턴 — 하락 추세 종료 강력 시그널. H&S 의 거울상.

    When:
        Quant regime + AI 바닥 탈출 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        lows ≥ 3 + highs ≥ 2.

    Raises:
        없음.

    Example:
        >>> p = detectInvertedHS(pivots, close, dates)
        >>> p.direction if p else None
        'bullish'

    See Also:
        - detectHeadShoulders : 대칭 bearish
        - detectChartPatterns : 통합 진입점

    AIContext:
        역H&S 탐지 시 ``targetPrice`` 까지 상승 여력 답변. 신뢰도 높은 매수 신호.
    """
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
