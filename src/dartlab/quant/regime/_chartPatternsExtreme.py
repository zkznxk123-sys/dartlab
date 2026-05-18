"""차트 패턴 — Triple + Rounding 4 함수 (반전형 2)."""

from __future__ import annotations

import numpy as np

from dartlab.quant.regime._chartPatternsReversal import ChartPattern


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
