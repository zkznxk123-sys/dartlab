"""analysis/forecast/revenueForecast 세그먼트 + backlog 그룹 분리.

revenueForecast.py 가 1526 줄 god module 이라 세그먼트/backlog/시나리오 빌더 분리.
identity 보존을 위해 revenueForecast.py 가 본 모듈에서 re-export 한다.

함수:
- _extractSegmentForecasts — 세그먼트별 매출 forecast
- _segmentBottomUpGrowth — bottom-up 세그먼트 합계
- _computeBacklogSignal — 수주잔고/계약자산 → 6 개월 선행 시그널
- _buildScenarios — bull/base/bear 시나리오 path
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.analysis.forecast.revenueForecast import (
        BacklogSignal,
        SegmentForecast,
    )


def _lazy(name):
    """revenueForecast 본체 lazy lookup — 순환 회피."""
    import importlib

    return getattr(importlib.import_module("dartlab.analysis.forecast.revenueForecast"), name)


def __getattr__(name: str) -> object:
    """본체 module attribute lazy lookup (forecastMetric, _classifyLifecycle 등)."""
    return _lazy(name)


def forecastMetric(*args, **kwargs) -> dict | None:
    """revenueForecast.forecastMetric lazy proxy — 본체로 위임.

    Requires:
        dartlab.analysis.forecast.revenueForecast 모듈 import 가능.

    Raises:
        없음. 본체 함수의 예외 그대로 전파.

    Example:
        >>> forecastMetric(series, metric="revenue")
        ForecastResult(...)
    """
    return _lazy("forecastMetric")(*args, **kwargs)


def _classifyLifecycle(*args, **kwargs):
    """revenueForecast._classifyLifecycle lazy proxy — 본체로 위임."""
    return _lazy("_classifyLifecycle")(*args, **kwargs)


def _extractSegmentForecasts(
    segmentRevenue: object,  # pl.DataFrame | None (TYPE_CHECKING 회피)
    horizon: int = 3,
) -> list[SegmentForecast]:
    """세그먼트별 개별 시계열 예측.

    Parameters
    ----------
    segmentRevenue : pl.DataFrame | None
        세그먼트 매출 DataFrame (컬럼: "부문" + 연도).
    horizon : int
        예측 기간 (년, 기본 3).

    Returns
    -------
    list[SegmentForecast]
        세그먼트별 예측 결과 (비중 내림차순 정렬).
        데이터 부족 시 빈 리스트.
    """
    if segmentRevenue is None:
        return []

    import importlib.util

    if importlib.util.find_spec("polars") is None:
        return []

    df = segmentRevenue
    if not hasattr(df, "columns") or "부문" not in df.columns:
        return []

    # 연도 컬럼 추출 (숫자만)
    yearCols = sorted(
        [c for c in df.columns if c != "부문" and c.isdigit()],
        key=int,
    )
    if len(yearCols) < 3:
        return []

    totalLatest = 0.0
    segmentLatest: dict[str, float] = {}

    results: list[SegmentForecast] = []
    for row in df.iter_rows(named=True):
        name = row.get("부문", "")
        if not name:
            continue

        # 시계열 추출 (오래된 순서로)
        vals = [row.get(y) for y in yearCols]
        valid = [(i, v) for i, v in enumerate(vals) if v is not None and v > 0]
        if len(valid) < 3:
            continue

        # 최근 매출 (비중 계산용)
        latest = valid[-1][1]
        segmentLatest[name] = latest
        totalLatest += latest

        # forecastMetric에 넣기 위한 가짜 series dict 구성
        fakeSeries = {
            "IS": {"sales": [v for _, v in valid]},
        }
        fr = forecastMetric(fakeSeries, "revenue", horizon)
        if not fr.projected:
            continue

        # 라이프사이클 판정
        lc, _ = _classifyLifecycle(fakeSeries)

        # 성장률 계산
        growthRates: list[float] = []
        prevVal = latest
        for p in fr.projected:
            if prevVal > 0:
                growthRates.append(round((p / prevVal - 1) * 100, 1))
            else:
                growthRates.append(0.0)
            prevVal = p

        results.append(
            SegmentForecast(
                name=name,
                historical=[v for _, v in valid],
                projected=fr.projected,
                growthRates=growthRates,
                method=fr.method,
                shareOfRevenue=0.0,  # 후처리에서 계산
                lifecycle=lc,
            )
        )

    # 비중 계산
    if totalLatest > 0:
        for sf in results:
            latestRev = segmentLatest.get(sf.name, 0)
            sf.shareOfRevenue = round(latestRev / totalLatest * 100, 1)

    # 비중 내림차순 정렬
    results.sort(key=lambda x: x.shareOfRevenue, reverse=True)
    return results


def _segmentBottomUpGrowth(
    segmentForecasts: list[SegmentForecast],
    horizon: int,
    lastRevenue: float | None,
) -> list[float]:
    """세그먼트별 예측을 합산하여 Bottom-Up 성장률 시계열 생성.

    Parameters
    ----------
    segmentForecasts : list[SegmentForecast]
        세그먼트별 예측 결과.
    horizon : int
        예측 기간 (년).
    lastRevenue : float | None
        최근 총 매출 (원).

    Returns
    -------
    list[float]
        연도별 Bottom-Up 매출 성장률 (%).
        데이터 부족 시 빈 리스트.
    """
    if not segmentForecasts or not lastRevenue or lastRevenue <= 0:
        return []

    growthRates: list[float] = []
    # 세그먼트 합산: 각 연도별 세그먼트 projected 합
    prevTotal = sum(sf.historical[-1] for sf in segmentForecasts if sf.historical)
    if prevTotal <= 0:
        return []

    for yr in range(horizon):
        yrTotal = 0.0
        for sf in segmentForecasts:
            if yr < len(sf.projected):
                yrTotal += sf.projected[yr]
            elif sf.projected:
                yrTotal += sf.projected[-1]
        if prevTotal > 0:
            growthRates.append((yrTotal / prevTotal - 1) * 100)
        else:
            growthRates.append(0.0)
        prevTotal = yrTotal

    return growthRates


# ══════════════════════════════════════
# 수주잔고 선행지표 (Source 6)
# ══════════════════════════════════════


def _computeBacklogSignal(
    orderDf: object,  # pl.DataFrame | None
    salesDf: object,  # pl.DataFrame | None
    sectorKey: str | None = None,
) -> BacklogSignal | None:
    """수주잔고 기반 선행 시그널 계산.

    Parameters
    ----------
    orderDf : pl.DataFrame | None
        수주잔고 DataFrame.
    salesDf : pl.DataFrame | None
        매출 DataFrame.
    sectorKey : str, optional
        WICS 업종 키 (건설/조선/방산 강신호 판별).

    Returns
    -------
    BacklogSignal | None
        backlogRevenueRatio : float — B/R ratio (배)
        brRatioTrend : str — 추세 ("increasing" | "stable" | "declining")
        impliedRevenueGrowth : float — 내재 매출 성장률 (%)
        conversionRate : float — 수주→매출 전환율 (비율)
        sectorsApplicable : bool — 강신호 업종 여부
        데이터 부족 시 None.
    """
    if orderDf is None or salesDf is None:
        return None

    if not hasattr(orderDf, "columns") or not hasattr(salesDf, "columns"):
        return None

    try:
        # 수주잔고 합산 (모든 행의 마지막 value 컬럼 합)
        orderValCols = [c for c in orderDf.columns if c != "label"]
        salesValCols = [c for c in salesDf.columns if c != "label"]

        if not orderValCols or not salesValCols:
            return None

        # 최신 기간 수주잔고 합산
        latestOrderCol = orderValCols[0]  # 첫 컬럼이 최근
        latestSalesCol = salesValCols[0]

        orderTotal = 0.0
        for row in orderDf.iter_rows(named=True):
            v = row.get(latestOrderCol)
            if v is not None and isinstance(v, (int, float)):
                orderTotal += abs(v)

        salesTotal = 0.0
        for row in salesDf.iter_rows(named=True):
            v = row.get(latestSalesCol)
            if v is not None and isinstance(v, (int, float)):
                salesTotal += abs(v)

        if salesTotal <= 0 or orderTotal <= 0:
            return None

        brRatio = orderTotal / salesTotal

        # B/R ratio 추세 (2기간 이상 필요)
        brRatios: list[float] = []
        nPeriods = min(len(orderValCols), len(salesValCols))
        for i in range(min(nPeriods, 3)):
            oCol = orderValCols[i]
            sCol = salesValCols[i]
            oSum = sum(
                abs(row.get(oCol, 0) or 0)
                for row in orderDf.iter_rows(named=True)
                if isinstance(row.get(oCol), (int, float))
            )
            sSum = sum(
                abs(row.get(sCol, 0) or 0)
                for row in salesDf.iter_rows(named=True)
                if isinstance(row.get(sCol), (int, float))
            )
            if sSum > 0:
                brRatios.append(oSum / sSum)

        # 추세 판단
        if len(brRatios) >= 2:
            if brRatios[0] > brRatios[-1] * 1.05:
                trend = "increasing"
            elif brRatios[0] < brRatios[-1] * 0.95:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # 내재 매출 성장률: B/R ratio 변화 → 매출 성장 추정
        if len(brRatios) >= 2 and brRatios[-1] > 0:
            impliedGrowth = (brRatios[0] / brRatios[-1] - 1) * 100
        else:
            impliedGrowth = 0.0

        # 전환율: 역사적 평균 (매출/수주잔고)
        conversionRate = 1.0 / brRatio if brRatio > 0 else 0.0

        # 건설/조선/방산: 수주잔고가 특히 강한 선행지표인 섹터 (정보 목적)
        _strongSectors = {"건설", "조선", "방산", "건설/토목", "조선/기계"}
        isApplicable = bool(sectorKey and any(s in sectorKey for s in _strongSectors))

        return BacklogSignal(
            backlogRevenueRatio=round(brRatio, 2),
            brRatioTrend=trend,
            impliedRevenueGrowth=round(impliedGrowth, 1),
            conversionRate=round(conversionRate, 3),
            sectorsApplicable=isApplicable,
        )
    except (TypeError, ValueError, KeyError):
        return None


# ══════════════════════════════════════
# 3-시나리오 빌더 (Base/Bull/Bear)
# ══════════════════════════════════════

# 라이프사이클별 spread 배수 (1σ 대비)
_LIFECYCLE_SPREAD = {
    "high_growth": 1.5,
    "mature": 0.7,
    "transition": 2.0,
    "decline": 1.2,
    "unknown": 1.0,
}


def _buildScenarios(
    projected: list[float],
    growthRates: list[float],
    historical: list[float | None],
    lifecycle: str,
    lastRevenue: float | None,
    structuralBreak: dict | None = None,
) -> tuple[dict[str, list[float]], dict[str, list[float]], dict[str, float]]:
    """Base/Bull/Bear 3-시나리오 생성."""
    if not projected or not lastRevenue or lastRevenue <= 0:
        return {}, {}, {}

    # 과거 성장률 변동성 (σ) 계산
    validHist = [v for v in historical if v is not None and v > 0]
    histGrowth: list[float] = []
    for i in range(1, len(validHist)):
        if validHist[i - 1] > 0:
            histGrowth.append((validHist[i] / validHist[i - 1] - 1) * 100)

    if histGrowth:
        meanG = sum(histGrowth) / len(histGrowth)
        variance = sum((g - meanG) ** 2 for g in histGrowth) / max(len(histGrowth) - 1, 1)
        sigma = math.sqrt(variance)
    else:
        sigma = 5.0  # 기본 5%p

    # 최소 sigma 보장 (너무 좁은 밴드 방지)
    sigma = max(sigma, 3.0)

    spread = _LIFECYCLE_SPREAD.get(lifecycle, 1.0)

    scenarios: dict[str, list[float]] = {"base": list(projected)}
    scenarioGrs: dict[str, list[float]] = {"base": list(growthRates)}

    # Bull / Bear
    for label, direction in [("bull", 1.0), ("bear", -1.0)]:
        scProjected: list[float] = []
        scGrs: list[float] = []
        prev = lastRevenue
        for i, gr in enumerate(growthRates):
            # 시간 감쇠: 멀수록 불확실성 증가
            timeFactor = 1.0 + i * 0.15
            adjGr = gr + direction * sigma * spread * timeFactor
            # Bull cap: 2× base growth, Bear floor: -base growth (mature 이상)
            if direction > 0:
                adjGr = min(adjGr, max(gr * 2, gr + 20))
            else:
                if lifecycle != "decline":
                    adjGr = max(adjGr, min(gr * 0.5, gr - 20))
            val = prev * (1 + adjGr / 100)
            scProjected.append(val)
            scGrs.append(round(adjGr, 1))
            prev = val
        scenarios[label] = scProjected
        scenarioGrs[label] = scGrs

    # 구조변화 감지 시 시나리오 확률 조정 (하방 리스크 확대)
    stability = structuralBreak.get("overallStability", "stable") if structuralBreak else "stable"
    if stability == "volatile":
        probabilities = {"base": 40.0, "bull": 20.0, "bear": 40.0}
    elif stability == "transitioning":
        probabilities = {"base": 45.0, "bull": 22.0, "bear": 33.0}
    else:
        probabilities = {"base": 50.0, "bull": 25.0, "bear": 25.0}

    return scenarios, scenarioGrs, probabilities


# ══════════════════════════════════════
# 메인 예측 함수
# ══════════════════════════════════════


__all__ = [
    "_buildScenarios",
    "_computeBacklogSignal",
    "_extractSegmentForecasts",
    "_segmentBottomUpGrowth",
]
