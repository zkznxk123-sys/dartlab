"""forecast 의 scenarioAnalysis + sensitivityAnalysis."""

from __future__ import annotations

from dartlab.analysis.forecast._forecastMetric import forecastMetric
from dartlab.analysis.forecast._forecastTypes import (
    ForecastResult,
    ScenarioResult,
    SensitivityResult,
)
from dartlab.core.utils.extract import getAnnualValues
from dartlab.core.utils.fmt import fmtBig, fmtPrice
from dartlab.core.utils.ols import _ols
from dartlab.frame.sector import SectorParams


def scenarioAnalysis(
    series: dict,
    shares: int | None = None,
    sectorParams: SectorParams | None = None,
    currentPrice: float | None = None,
) -> ScenarioResult:
    """3-Scenario DCF 분석 — Bull/Base/Bear 확률가중 적정가.

    Capabilities:
        - Bull/Base/Bear 3 시나리오 DCF 적정가 산출
        - 확률 가중 단일 주당 가치 합산

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    shares : int, optional
        발행주식수.
    sectorParams : SectorParams, optional
        업종별 파라미터 (할인율, 성장률, 멀티플).
    currentPrice : float, optional
        현재 주가 (원).

    Returns
    -------
    ScenarioResult
        base : dict — Base 시나리오 (growth, discountRate, perShareValue 등)
        bull : dict — Bull 시나리오
        bear : dict — Bear 시나리오
        probability : dict — 시나리오별 확률 (%)
        weightedValue : float | None — 확률가중 주당 적정가 (원)
        currentPrice : float | None — 현재 주가 (원)

    Guide:
        DCF 3 회 호출 + 50/25/25 가중치로 단일 weightedValue 산출.

    When:
        단일 DCF 적정가가 아닌 확률 가중 적정가가 필요할 때.

    How:
        dcfValuation 을 base/bull/bear 파라미터로 3 회 호출.

    Requires:
        valuation.dcf 의 dcfValuation 함수.

    Raises:
        없음. FCF 부족 시 warnings 누적.

    Example:
        >>> r = scenarioAnalysis(series, shares=1_000_000)
        >>> r.probability["base"]
        50

    See Also:
        - calibrateScenarios : 외부 신호로 확률 보정
        - sensitivityAnalysis : WACC × 성장률 민감도

    AIContext:
        AI 답변 시 weightedValue 와 시나리오별 perShareValue 표로 인용.
    """
    from dartlab.analysis.valuation.dcf import DCFResult, dcfValuation

    warnings: list[str] = []
    sp = sectorParams or SectorParams(
        discountRate=10.0,
        growthRate=3.0,
        perMultiple=15,
        pbrMultiple=1.2,
        evEbitdaMultiple=8,
        label="기타",
    )

    baseDcf = dcfValuation(series, shares=shares, sectorParams=sp, currentPrice=currentPrice)
    bullDcf = dcfValuation(
        series,
        shares=shares,
        sectorParams=sp,
        currentPrice=currentPrice,
        discountRate=max(sp.discountRate - 1.0, 5.0),
        terminalGrowth=min(sp.growthRate, 3.0) + 0.5,
    )
    bearDcf = dcfValuation(
        series,
        shares=shares,
        sectorParams=sp,
        currentPrice=currentPrice,
        discountRate=sp.discountRate + 1.0,
        terminalGrowth=max(min(sp.growthRate, 3.0) - 0.5, 0.5),
    )

    def _scenarioDict(dcf: DCFResult) -> dict[str, float | None]:
        """DCFResult를 시나리오 요약 dict로 변환."""
        return {
            "growth": dcf.growthRateInitial,
            "discountRate": dcf.discountRate,
            "terminalGrowth": dcf.terminalGrowth,
            "enterpriseValue": dcf.enterpriseValue,
            "equityValue": dcf.equityValue,
            "perShareValue": dcf.perShareValue,  # None 보존 (DCF 결손 시)
        }

    base = _scenarioDict(baseDcf)
    bull = _scenarioDict(bullDcf)
    bear = _scenarioDict(bearDcf)

    prob = {"base": 50, "bull": 25, "bear": 25}

    weighted = None
    baseV = base.get("perShareValue", 0)
    bullV = bull.get("perShareValue", 0)
    bearV = bear.get("perShareValue", 0)
    if baseV > 0 or bullV > 0 or bearV > 0:
        weighted = round(
            baseV * prob["base"] / 100 + bullV * prob["bull"] / 100 + bearV * prob["bear"] / 100,
            0,
        )

    if not baseDcf.fcfProjections:
        warnings.append("FCF 데이터 부족 → 시나리오 분석 신뢰도 낮음")

    return ScenarioResult(
        base=base,
        bull=bull,
        bear=bear,
        probability=prob,
        weightedValue=weighted,
        currentPrice=currentPrice,
        warnings=warnings,
    )


# ── 민감도 분석 ──────────────────────────────────────────


def sensitivityAnalysis(
    series: dict,
    shares: int | None = None,
    sectorParams: SectorParams | None = None,
    waccSteps: int = 5,
    waccRange: float = 2.0,
    growthSteps: int = 5,
    growthRange: float = 1.0,
) -> SensitivityResult:
    """WACC x Terminal Growth 민감도 테이블.

    Capabilities:
        - WACC × 영구성장률 격자 DCF 주당가치 매트릭스 산출
        - 기준값 대비 상하 범위 자동 격자 생성

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    shares : int, optional
        발행주식수.
    sectorParams : SectorParams, optional
        업종별 파라미터.
    waccSteps : int
        WACC 축 단계 수 (기본 5).
    waccRange : float
        WACC 기준 대비 상하 범위 (%p, 기본 2.0).
    growthSteps : int
        영구성장률 축 단계 수 (기본 5).
    growthRange : float
        영구성장률 기준 대비 상하 범위 (%p, 기본 1.0).

    Returns
    -------
    SensitivityResult
        waccValues : list[float] — WACC 축 값 (%)
        growthValues : list[float] — 영구성장률 축 값 (%)
        matrix : list[list[float]] — 주당 가치 매트릭스 (원)
        baseWacc : float — 기준 WACC (%)
        baseGrowth : float — 기준 영구성장률 (%)
        baseValue : float — 기준 주당 가치 (원)

    Guide:
        DCF 결과 변동성을 매트릭스 히트맵으로 시각화하는 데이터 소스.

    When:
        단일 적정가가 아닌 입력 가정에 따른 가치 범위가 필요할 때.

    How:
        dcfValuation 을 waccSteps × growthSteps 격자만큼 반복 호출.

    Requires:
        valuation.dcf 의 dcfValuation 함수.

    Raises:
        없음. 결손 격자는 0 처리.

    Example:
        >>> r = sensitivityAnalysis(series, shares=1_000_000)
        >>> len(r.matrix)
        5

    See Also:
        - scenarioAnalysis : 3 시나리오 확률 가중
        - dcfValuation : 단일 적정가

    AIContext:
        AI 답변 시 매트릭스 min/max 범위로 가치 폭 표시.
    """
    from dartlab.analysis.valuation.dcf import dcfValuation

    sp = sectorParams or SectorParams(
        discountRate=10.0,
        growthRate=3.0,
        perMultiple=15,
        pbrMultiple=1.2,
        evEbitdaMultiple=8,
        label="기타",
    )

    baseWacc = sp.discountRate
    baseGrowth = min(sp.growthRate, 3.0)

    waccLo = max(baseWacc - waccRange, 4.0)
    waccHi = baseWacc + waccRange
    waccStep = (waccHi - waccLo) / max(waccSteps - 1, 1)
    waccValues = [round(waccLo + i * waccStep, 1) for i in range(waccSteps)]

    growthLo = max(baseGrowth - growthRange, 0.5)
    growthHi = baseGrowth + growthRange
    gStep = (growthHi - growthLo) / max(growthSteps - 1, 1)
    gValues = [round(growthLo + i * gStep, 1) for i in range(growthSteps)]

    matrix: list[list[float]] = []
    bValue = 0.0

    for wacc in waccValues:
        row: list[float] = []
        for tg in gValues:
            if wacc <= tg:
                row.append(0)
                continue
            dcf = dcfValuation(
                series,
                shares=shares,
                sectorParams=sp,
                discountRate=wacc,
                terminalGrowth=tg,
            )
            val = dcf.perShareValue or 0
            row.append(val)
            if abs(wacc - baseWacc) < 0.05 and abs(tg - baseGrowth) < 0.05:
                bValue = val
        matrix.append(row)

    return SensitivityResult(
        waccValues=waccValues,
        growthValues=gValues,
        matrix=matrix,
        baseWacc=baseWacc,
        baseGrowth=baseGrowth,
        baseValue=bValue,
    )
