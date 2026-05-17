"""거시 차트 패턴 자동 인식 — W/M, H&S, 삼중바닥/천장, 원형천장/바닥.

캔들 9패턴(quant/pattern.py)이 단일 봉/2-3봉 단위라면,
이 모듈은 zigzag pivot 기반의 거시 패턴을 탐지한다.

각 패턴은 형성 시점, 신뢰도(0-1), 목표가(있으면)를 반환한다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.regime.pattern import _findPivots
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


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


def detectTripleBottom(pivots: list[dict], prices: np.ndarray, dates: list) -> ChartPattern | None:
    """삼중바닥: 3개 저점이 비슷한 수준.

    Capabilities:
        - 3 저점이 평균 대비 ±3% 이내 + 사이 고점 평균 = 저항선 + 현재가가 저항선 돌파 시 탐지
        - 저항선과 평균저점 폭만큼 상승 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과.
        prices: 종가 배열.
        dates: 날짜 리스트.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bullish"``.

    Guide:
        쌍바닥 보다 신뢰도 높은 반전 패턴. 3 회 지지 + 저항선 돌파.

    When:
        Quant regime + AI 강한 매수 시그널 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        lows ≥ 3 + highs ≥ 2.

    Raises:
        없음.

    Example:
        >>> p = detectTripleBottom(pivots, close, dates)
        >>> p.confidence if p else None
        0.82

    See Also:
        - detectDoubleBottom : 2 저점 버전
        - detectTripleTop : 대칭 bearish

    AIContext:
        삼중바닥 탐지 시 "3 회 지지 + 저항선 돌파, 강력 매수" 답변.
    """
    lows = [p for p in pivots if p["type"] == "low"]
    if len(lows) < 3:
        return None

    l3, l2, l1 = lows[-3], lows[-2], lows[-1]
    avg = (l1["price"] + l2["price"] + l3["price"]) / 3
    max_diff = max(abs(p["price"] - avg) / avg for p in (l1, l2, l3))
    if max_diff > 0.03:
        return None

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
    """삼중천장: 3개 고점이 비슷한 수준.

    Capabilities:
        - 3 고점이 평균 대비 ±3% 이내 + 사이 저점 평균 = 지지선 + 현재가가 지지선 하향 이탈 시 탐지
        - 지지선과 평균고점 폭만큼 하락 목표가 산출

    Args:
        pivots: ``_findPivots`` 결과.
        prices: 종가 배열.
        dates: 날짜 리스트.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bearish"``.

    Guide:
        쌍봉 보다 신뢰도 높은 반전 패턴. 3 회 저항 + 지지선 이탈.

    When:
        Quant regime + AI 강한 매도 시그널 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        highs ≥ 3 + lows ≥ 2.

    Raises:
        없음.

    Example:
        >>> p = detectTripleTop(pivots, close, dates)
        >>> p.direction if p else None
        'bearish'

    See Also:
        - detectDoubleTop : 2 고점 버전
        - detectTripleBottom : 대칭 bullish

    AIContext:
        삼중천장 탐지 시 "3 회 저항 + 지지 이탈, 강력 매도" 답변.
    """
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
    """원형바닥: 최근 window 구간에 2차 다항식 fit, 계수>0, R² 충분.

    Capabilities:
        - window 일 종가에 2차 polyfit → 계수 a > 0 (아래 볼록) + R² ≥ 0.7 + 현재가 > midpoint 시 탐지
        - 대전환 신호 — 장기 누적 매집 후 회복

    Args:
        prices: 종가 배열.
        dates: 날짜 리스트.
        window: 분석 구간 길이. 기본 ``60`` 일.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bullish"``, ``targetPrice=None`` (표준 공식 부재).

    Guide:
        장기 추세 반전. 거래량 점진 증가 + ``r2 ≥ 0.7`` 면 강한 시그널.

    When:
        Quant regime + AI 장기 매수 시점 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        prices ≥ window (60 일 이상).

    Raises:
        없음 — 데이터 부족·계수 음수 시 None.

    Example:
        >>> p = detectRoundingBottom(close, dates, window=60)
        >>> p.direction if p else None
        'bullish'

    See Also:
        - detectRoundingTop : 대칭 bearish
        - detectChartPatterns : 통합 진입점

    AIContext:
        원형바닥 탐지 시 "장기 누적 매집 회복, 대전환 신호 (R²=X)" 답변.
    """
    if len(prices) < window:
        return None

    y = prices[-window:]
    x = np.arange(window, dtype=float)
    coeffs = np.polyfit(x, y, 2)
    a = coeffs[0]
    if a <= 0:
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
    if prices[-1] <= midpoint:
        return None

    return ChartPattern(
        name="roundingBottom",
        label="원형바닥",
        formedAt=str(dates[-1])[:10],
        confidence=round(min(1.0, r2), 2),
        targetPrice=None,
        direction="bullish",
        description=f"원형바닥 — {window}일 2차 fit (a={a:.4f}, R²={r2:.2f}), 대전환 신호",
    )


def detectRoundingTop(prices: np.ndarray, dates: list, window: int = 60) -> ChartPattern | None:
    """원형천장: 2차 다항식 계수<0.

    Capabilities:
        - window 일 종가에 2차 polyfit → 계수 a < 0 (위 볼록) + R² ≥ 0.7 + 현재가 < midpoint 시 탐지
        - 대전환 신호 — 장기 누적 분산 후 하락 시작

    Args:
        prices: 종가 배열.
        dates: 날짜 리스트.
        window: 분석 구간 길이. 기본 ``60`` 일.

    Returns:
        ChartPattern | None — 탐지 시 ``direction="bearish"``, ``targetPrice=None``.

    Guide:
        장기 추세 반전. 천장 형성 + 거래량 감소 동반 시 강력.

    When:
        Quant regime + AI 장기 매도 시점 답변.

    How:
        ``detectChartPatterns`` 통합 진입점에서 호출.

    Requires:
        prices ≥ window.

    Raises:
        없음.

    Example:
        >>> p = detectRoundingTop(close, dates, window=60)
        >>> p.direction if p else None
        'bearish'

    See Also:
        - detectRoundingBottom : 대칭 bullish
        - detectChartPatterns : 통합 진입점

    AIContext:
        원형천장 탐지 시 "장기 분산 시작, 대전환 매도 신호 (R²=X)" 답변.
    """
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
    pivotThreshold: float = 0.05,
) -> list[ChartPattern]:
    """모든 거시 차트 패턴을 한 번에 탐지.

    Capabilities:
        - zigzag pivot 추출 후 8 패턴 (W/M/H&S/iH&S/3B/3T/원형B/원형T) 일괄 적용
        - confidence 내림차순 정렬 + 예외 패턴 skip

    Args:
        high: 고가 배열.
        low: 저가 배열.
        close: 종가 배열.
        dates: 날짜 리스트.
        pivotThreshold: zigzag pivot 임계값. 기본 ``0.05`` (5%).

    Returns:
        list[ChartPattern] — 탐지된 패턴 리스트 (confidence 내림차순). 미탐지 시 ``[]``.

    Guide:
        ``calcChartPatterns`` 의 핵심 엔진. zigzag 5% 임계는 한국 KOSPI 표준.
        강세장에서 임계 ↓, 횡보장에서 임계 ↑ 권장.

    When:
        Quant regime 패턴 축 + AI 추세 전환 답변.

    How:
        ``_findPivots`` 로 zigzag 추출 → 8 detector lambda 순회 → 예외 skip → 정렬.

    Requires:
        OHLC 시계열 ≥ 30 일.

    Raises:
        없음 — 개별 detector 의 ValueError/IndexError/ZeroDivisionError 는 skip.

    Example:
        >>> patterns = detectChartPatterns(h, l, c, dates)
        >>> [p.name for p in patterns]
        ['doubleBottom', 'roundingBottom']

    See Also:
        - calcChartPatterns : quant 축 진입점 (종목 코드 → patterns)
        - _findPivots : zigzag pivot 추출
        - detectDoubleBottom 외 7 함수 : 개별 detector

    AIContext:
        다중 패턴 동시 탐지 결과를 "패턴 N 개 동시 신호, 최고 confidence X" 형태로 답변.
    """
    if len(close) < 30:
        return []

    pivots = _findPivots(high, low, threshold=pivotThreshold)
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


def calcChartPatterns(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """quant 축 진입점 — 거시 차트 패턴 자동 탐지.

    Capabilities:
        - 종목코드 → OHLC fetch → 8 패턴 일괄 탐지 → dict 직렬화
        - confidence 내림차순 patterns list + dataPoints 메타

    Args:
        stockCode: 종목코드 또는 ticker.
        market: ``"KR" | "US" | "auto"``. 기본 ``"auto"``.
        **kwargs: ``fetchOhlcv`` 에 전달 (period/end 등).

    Returns:
        dict
            stockCode : str
            market : str
            dataPoints : int — 분석 데이터 수
            patterns : list[dict] — 각 dict 에 name/label/formedAt/confidence/direction/targetPrice/description
            error : str — 데이터 부족·없음 시

    Guide:
        Quant 축 표준 진입점. dataPoints ≥ 30 필수. 신뢰도 ≥ 0.7 패턴 우선.

    When:
        Quant regime 패턴 축 평가 + AI 차트 패턴 답변.

    How:
        ``resolveMarket`` → ``fetchOhlcv`` → ``ohlcvToArrays`` → ``detectChartPatterns``.

    Requires:
        주가 OHLC 시계열 ≥ 30 일.

    Raises:
        없음 — 데이터 부족 시 ``{"error": ...}`` 반환.

    Example:
        >>> r = calcChartPatterns("005930", market="KR")
        >>> len(r["patterns"])
        2

    See Also:
        - detectChartPatterns : 핵심 패턴 엔진
        - fetchOhlcv : OHLC 데이터 로드

    AIContext:
        AI 가 "삼성전자 차트 패턴 보여줘" 류 질문에 ``patterns[0]`` 의 label + targetPrice + confidence 인용.
    """
    market = resolveMarket(stockCode, market)
    ohlcv = fetchOhlcv(stockCode, **kwargs)
    if isEmptyDf(ohlcv):
        return {"error": f"{stockCode} 주가 데이터 없음"}

    arr = ohlcvToArrays(ohlcv)
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
