"""거시 차트 패턴 자동 인식 — facade. 본체는 `_chartPatternsReversal` + `_chartPatternsExtreme`.

캔들 9패턴(quant/pattern.py)이 단일 봉/2-3봉 단위라면,
이 모듈은 zigzag pivot 기반의 거시 패턴을 탐지한다.

각 패턴은 형성 시점, 신뢰도(0-1), 목표가(있으면)를 반환한다.
"""

from __future__ import annotations

import numpy as np

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.regime._chartPatternsExtreme import (
    detectRoundingBottom,
    detectRoundingTop,
    detectTripleBottom,
    detectTripleTop,
)
from dartlab.quant.regime._chartPatternsReversal import (
    ChartPattern,
    detectDoubleBottom,
    detectDoubleTop,
    detectHeadShoulders,
    detectInvertedHS,
)
from dartlab.quant.regime.pattern import _findPivots
from dartlab.quant.screen.dataAccess import fetchOhlcv, ohlcvToArrays


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


__all__ = [
    "ChartPattern",
    "calcChartPatterns",
    "detectChartPatterns",
    "detectDoubleBottom",
    "detectDoubleTop",
    "detectHeadShoulders",
    "detectInvertedHS",
    "detectRoundingBottom",
    "detectRoundingTop",
    "detectTripleBottom",
    "detectTripleTop",
]
