"""forecast 의 forecastMetric + _marginLinkedForecast + forecastAll."""

from __future__ import annotations

from dartlab.analysis.forecast._forecastTypes import (
    _FALLBACKS,
    FORECAST_TARGETS,
    ForecastResult,
)
from dartlab.core.utils.extract import getAnnualValues
from dartlab.core.utils.ols import (
    _coefficientOfVariation,
    _detectStructuralBreak,
    _ols,
)
from dartlab.frame.sector import SectorParams


def forecastMetric(
    series: dict,
    metric: str = "revenue",
    horizon: int = 3,
    sectorParams: SectorParams | None = None,
) -> ForecastResult:
    """단일 메트릭 시계열 예측.

    Capabilities:
        - OLS·CAGR decay·평균회귀 3 모델 자동 선택
        - 구조적 전환 감지 후 후행 구간만 학습

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    metric : str
        예측 대상 ("revenue", "operating_income", "net_income", "operating_cashflow").
    horizon : int
        예측 기간 (년, 기본 3).
    sectorParams : SectorParams, optional
        업종별 파라미터 (성장률 등).

    Returns
    -------
    ForecastResult
        metric : str — 예측 대상 코드
        metricLabel : str — 한글 라벨
        historical : list[float | None] — 과거 연간 실적 (원)
        projected : list[float] — 예측값 시계열 (원)
        horizon : int — 예측 기간 (년)
        method : str — 사용 모델 ("linear" | "cagr_decay" | "mean_revert")
        confidence : str — 신뢰도 ("high" | "medium" | "low")
        rSquared : float — 결정계수 (0~1)
        growthRate : float — 적용 성장률 (%)

    Guide:
        finance.timeseries dict 한 개 + metric 키 하나로 단일 항목 예측.

    When:
        단일 재무 항목의 향후 3~5 년 예측이 필요할 때.

    How:
        forecastAll 내부에서 항목별 반복 호출되거나 단독 사용.

    Requires:
        timeseries 에 해당 metric annual 값 ≥ 3 개.

    Raises:
        없음. 데이터 부족 시 ForecastResult.warnings 에 사유 누적.

    Example:
        >>> r = forecastMetric(series, metric="revenue", horizon=3)
        >>> r.method in ("linear", "cagr_decay", "mean_revert", "N/A")
        True

    See Also:
        - forecastAll : 다중 메트릭 일괄 예측
        - scenarioAnalysis : optimistic/baseline/adverse 시나리오

    AIContext:
        AI 답변 시 method·confidence·rSquared 를 함께 인용해 신뢰도 표시.
    """
    warnings: list[str] = []
    target = FORECAST_TARGETS.get(metric)
    if target is None:
        return ForecastResult(
            metric=metric,
            metricLabel=metric,
            historical=[],
            projected=[],
            horizon=horizon,
            method="N/A",
            confidence="low",
            rSquared=0,
            growthRate=0,
            warnings=[f"미지원 예측 대상: {metric}"],
        )

    sjDiv, snakeId, label = target

    vals = getAnnualValues(series, sjDiv, snakeId)
    if not any(v is not None for v in vals):
        for fb in _FALLBACKS.get(snakeId, []):
            vals = getAnnualValues(series, sjDiv, fb)
            if any(v is not None for v in vals):
                break

    validPairs = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(validPairs) < 3:
        return ForecastResult(
            metric=metric,
            metricLabel=label,
            historical=vals,
            projected=[],
            horizon=horizon,
            method="N/A",
            confidence="low",
            rSquared=0,
            growthRate=0,
            warnings=["예측 불가: 유효 데이터 3년 미만"],
        )

    xVals = [float(p[0]) for p in validPairs]
    yVals = [p[1] for p in validPairs]

    breakIdx = _detectStructuralBreak(yVals, minSegment=4)
    if breakIdx is not None and breakIdx < len(yVals):
        nBefore = breakIdx
        nAfter = len(yVals) - breakIdx
        if nAfter >= 3:
            warnings.append(f"구조적 전환 감지 (데이터 {nBefore}→{nAfter}개 분할) — 전환 이후 데이터 기반 예측")
            xVals = xVals[breakIdx:]
            yVals = yVals[breakIdx:]

    cv = _coefficientOfVariation(yVals)
    slope, intercept, r2 = _ols(xVals, yVals)

    n = len(yVals)
    if yVals[0] > 0 and yVals[-1] > 0:
        cagr = ((yVals[-1] / yVals[0]) ** (1 / max(n - 1, 1)) - 1) * 100
    else:
        cagr = 0.0

    sectorGrowth = sectorParams.growthRate if sectorParams else 3.0

    if cv > 0.4:
        method = "mean_revert"
        meanVal = sum(yVals) / n
        projected = []
        last = yVals[-1]
        for yr in range(1, horizon + 1):
            blend = yr / (horizon + 1)
            proj = last * (1 - blend) + meanVal * blend
            projected.append(proj)
        growthRate = 0.0
        warnings.append("높은 변동성 → 평균 회귀 모델 적용")
    elif r2 > 0.7 and abs(cagr) < 30:
        method = "linear"
        lastX = xVals[-1]
        projected = [slope * (lastX + yr) + intercept for yr in range(1, horizon + 1)]
        growthRate = cagr
        for i, p in enumerate(projected):
            if p < 0 and yVals[-1] > 0:
                projected[i] = yVals[-1] * 0.5
                warnings.append(f"+{i + 1}년 예측이 음수 → 최근값의 50%로 대체")
    else:
        method = "cagr_decay"
        growth = min(max(cagr, -10), 25)
        terminal = sectorGrowth
        projected = []
        last = yVals[-1]
        for yr in range(1, horizon + 1):
            blend = (yr - 1) / max(horizon - 1, 1)
            g = growth * (1 - blend) + terminal * blend
            proj = last * (1 + g / 100)
            projected.append(proj)
            last = proj
        growthRate = growth

    if r2 > 0.8 and n >= 5:
        confidence = "high"
    elif r2 > 0.5 and n >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    assumptions = []
    if method == "linear":
        assumptions.append(f"선형 추세 연장 (R²={r2:.2f})")
    elif method == "cagr_decay":
        assumptions.append(f"CAGR {cagr:.1f}% → 섹터평균 {sectorGrowth:.1f}%로 감속")
    elif method == "mean_revert":
        meanVal = sum(yVals) / n
        assumptions.append(f"평균 {meanVal / 1e8:,.0f}억으로 회귀")
    assumptions.append(f"과거 {n}개년 데이터 기반")

    return ForecastResult(
        metric=metric,
        metricLabel=label,
        historical=vals,
        projected=projected,
        horizon=horizon,
        method=method,
        confidence=confidence,
        rSquared=round(r2, 3),
        growthRate=round(growthRate, 1),
        assumptions=assumptions,
        warnings=warnings,
    )


def _marginLinkedForecast(
    revResult: ForecastResult,
    series: dict,
    metric: str,
    horizon: int,
) -> ForecastResult | None:
    """매출 전망 × 마진 추세 → 영업이익/순이익 파생 예측.

    단순 OLS보다 정확: 매출 방향 예측(72~78%)을 이익에 전파.
    """
    if not revResult.projected or revResult.confidence == "low":
        return None

    target = FORECAST_TARGETS.get(metric)
    if target is None:
        return None
    sjDiv, snakeId, label = target

    # 과거 마진 계산
    revVals = getAnnualValues(series, "IS", "sales")
    if not any(v is not None for v in revVals):
        revVals = getAnnualValues(series, "IS", "revenue")
    metricVals = getAnnualValues(series, sjDiv, snakeId)
    for fb in _FALLBACKS.get(snakeId, []):
        if not any(v is not None for v in metricVals):
            metricVals = getAnnualValues(series, sjDiv, fb)

    margins = []
    for r, m in zip(revVals, metricVals):
        if r and m and r != 0:
            margins.append(m / r)

    if len(margins) < 2:
        return None

    # 최근 3년 마진 가중평균 (최신에 가중)
    recent = margins[-3:] if len(margins) >= 3 else margins
    weights = list(range(1, len(recent) + 1))
    wSum = sum(w * m for w, m in zip(weights, recent))
    avgMargin = wSum / sum(weights)

    # 매출 전망 × 마진 → 이익 전망
    projected = [rev * avgMargin for rev in revResult.projected]
    validHist = [v for v in metricVals if v is not None]
    lastVal = validHist[-1] if validHist else 0
    growthRate = ((projected[-1] / lastVal) ** (1 / horizon) - 1) * 100 if lastVal and lastVal > 0 else 0

    return ForecastResult(
        metric=metric,
        metricLabel=label,
        historical=metricVals,
        projected=projected,
        horizon=horizon,
        method=f"매출전망×마진({avgMargin:.1%})",
        confidence=revResult.confidence,
        rSquared=revResult.rSquared,
        growthRate=round(growthRate, 1),
        assumptions=[
            f"매출 전망 연동 (마진 {avgMargin:.1%} 적용)",
            f"최근 {len(recent)}년 가중평균 마진 사용",
        ],
        currency=revResult.currency,
    )


def forecastAll(
    series: dict,
    horizon: int = 3,
    sectorParams: SectorParams | None = None,
) -> dict[str, ForecastResult]:
    """모든 주요 메트릭 예측.

    매출은 정교한 앙상블, 영업이익/순이익은 매출x마진 연동.
    마진 연동 실패 시 단순 시계열 OLS fallback.

    Capabilities:
        - 매출·영업이익·순이익·OCF 4 메트릭 일괄 예측
        - 매출 기반 마진 연동 + OLS fallback 자동 전환

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    horizon : int
        예측 기간 (년, 기본 3).
    sectorParams : SectorParams, optional
        업종별 파라미터.

    Returns
    -------
    dict[str, ForecastResult]
        메트릭 키 → ForecastResult 매핑.
        키: "revenue", "operating_income", "net_income", "operating_cashflow".

    Guide:
        forecastMetric 을 4 번 호출하는 진입점. DCF 사전 단계로 사용.

    When:
        예측 대시보드·DCF 입력·시나리오 분석 전 일괄 예측이 필요할 때.

    How:
        forecastMetric (revenue) → marginLinkedForecast 또는 forecastMetric 반복.

    Requires:
        finance.timeseries dict 1 개.

    Raises:
        없음. 항목별 실패는 ForecastResult.warnings 누적.

    Example:
        >>> r = forecastAll(series, horizon=3)
        >>> "revenue" in r
        True

    See Also:
        - forecastMetric : 단일 메트릭
        - scenarioAnalysis : 시나리오 가중

    AIContext:
        AI 답변 시 메트릭별 method + confidence 표로 인용.
    """
    results: dict[str, ForecastResult] = {}

    # 매출 먼저
    revResult = forecastMetric(series, metric="revenue", horizon=horizon, sectorParams=sectorParams)
    results["revenue"] = revResult

    # 영업이익/순이익: 매출×마진 연동 우선, fallback OLS
    for key in ("operating_income", "net_income"):
        linked = _marginLinkedForecast(revResult, series, key, horizon)
        if linked is not None:
            results[key] = linked
        else:
            results[key] = forecastMetric(series, metric=key, horizon=horizon, sectorParams=sectorParams)

    # OCF는 단독 예측
    results["operating_cashflow"] = forecastMetric(
        series, metric="operating_cashflow", horizon=horizon, sectorParams=sectorParams
    )

    return results


# ── 시나리오 분석 ──────────────────────────────────────────
