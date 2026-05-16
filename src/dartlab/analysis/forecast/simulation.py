"""경제 시나리오 기반 시뮬레이션 예측 엔진.

3-Layer 구조:
1. MacroScenario — 거시경제 변수 경로 (GDP, 금리, 환율, CPI)
2. SectorElasticity — 업종별 거시경제 감응도 (beta)
3. CompanySimulation — 기업 실적 시뮬레이션 (시나리오 + Monte Carlo + 스트레스)

외부 의존성 제로 (random 모듈만 사용).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# ── 내부 유틸 ──
from dartlab.analysis.forecast._simHistorical import (
    HISTORICAL_SCENARIOS,
    _getActualRevChange,
    _getRevByYear,
    backtestSimulation,
    simulateHistorical,
)

# ══════════════════════════════════════
# Layer 3: 기업 시뮬레이션
# ══════════════════════════════════════
# ── 결과 타입 (분리: _simTypes.py SSOT, re-export 으로 BC 보존) ──
from dartlab.analysis.forecast._simTypes import (
    BacktestResult,
    MonteCarloResult,
    SimulationResult,
    StressTestResult,
)
from dartlab.core.utils.extract import (
    getAnnualValues,
    getLatest,
    getTTM,
)
from dartlab.core.utils.fmt import fmtBig, fmtPrice
from dartlab.frame.sector import SectorParams
from dartlab.synth.scenario import (
    BASELINE_FX,
    BASELINE_RATE,
    DEFAULT_ELASTICITY,
    PRESET_SCENARIOS,
    MacroScenario,
    SectorElasticity,
    getElasticity,
)


def _extractBaseMetrics(series: dict) -> dict[str, float | None]:
    """현재 기업 기본 지표 추출.

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.

    Returns
    -------
    dict
        revenue : float | None — TTM 매출 (원)
        operatingIncome : float | None — TTM 영업이익 (원)
        netIncome : float | None — TTM 순이익 (원)
        margin : float | None — 영업이익률 (%)
        ocf : float | None — 영업현금흐름 (원)
        fcf : float | None — 잉여현금흐름 (원)
        capex : float | None — 자본적지출 (원)
        dividendsPaid : float | None — 배당금 지급액 (원)
        totalAssets : float | None — 총자산 (원)
        totalEquity : float | None — 자기자본 (원)
        totalLiabilities : float | None — 총부채 (원)
        currentAssets : float | None — 유동자산 (원)
        currentLiabilities : float | None — 유동부채 (원)
        debtRatio : float | None — 부채비율 (%)
        currentRatio : float | None — 유동비율 (%)
        interestCoverage : float | None — 이자보상배율 (배)
        netDebt : float — 순차입금 (원)
        financeCosts : float | None — 금융비용 (원)
    """
    rev = getTTM(series, "IS", "sales") or getTTM(series, "IS", "revenue")
    oi = getTTM(series, "IS", "operating_profit") or getTTM(series, "IS", "operating_income")
    ni = getTTM(series, "IS", "net_profit") or getTTM(series, "IS", "net_income")
    ocf = getTTM(series, "CF", "operating_cashflow")
    capex = getTTM(series, "CF", "purchase_of_property_plant_and_equipment")
    div = getTTM(series, "CF", "dividends_paid")

    margin = (oi / rev * 100) if rev and oi and rev > 0 else None
    fcf = (ocf - abs(capex or 0)) if ocf is not None else None

    totalAssets = getLatest(series, "BS", "total_assets")
    totalEquity = getLatest(series, "BS", "total_stockholders_equity") or getLatest(
        series, "BS", "owners_of_parent_equity"
    )
    totalLiab = getLatest(series, "BS", "total_liabilities")
    currentAssets = getLatest(series, "BS", "current_assets")
    currentLiab = getLatest(series, "BS", "current_liabilities")
    cash = getLatest(series, "BS", "cash_and_cash_equivalents") or 0
    stb = getLatest(series, "BS", "shortterm_borrowings") or 0
    ltb = getLatest(series, "BS", "longterm_borrowings") or 0
    bonds = getLatest(series, "BS", "debentures") or 0
    finCosts = getTTM(series, "IS", "finance_costs") or getTTM(series, "IS", "interest_expense")

    debtRatio = (totalLiab / totalEquity * 100) if totalLiab and totalEquity and totalEquity > 0 else None
    currentRatio = (currentAssets / currentLiab * 100) if currentAssets and currentLiab and currentLiab > 0 else None
    interestCov = (oi / abs(finCosts)) if oi and finCosts and abs(finCosts) > 0 else None
    netDebt = stb + ltb + bonds - cash

    return {
        "revenue": rev,
        "operatingIncome": oi,
        "netIncome": ni,
        "margin": margin,
        "ocf": ocf,
        "fcf": fcf,
        "capex": capex,
        "dividendsPaid": div,
        "totalAssets": totalAssets,
        "totalEquity": totalEquity,
        "totalLiabilities": totalLiab,
        "currentAssets": currentAssets,
        "currentLiabilities": currentLiab,
        "debtRatio": debtRatio,
        "currentRatio": currentRatio,
        "interestCoverage": interestCov,
        "netDebt": netDebt,
        "financeCosts": finCosts,
    }


def _extractVolatility(series: dict) -> dict[str, float]:
    """과거 시계열에서 변동성 추출.

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.

    Returns
    -------
    dict
        revenueCv : float — 매출 변동계수 (비율, 0~1)
        marginStd : float — 영업이익률 표준편차 (%p)
    """
    revVals = getAnnualValues(series, "IS", "sales") or getAnnualValues(series, "IS", "revenue")
    oiVals = getAnnualValues(series, "IS", "operating_profit") or getAnnualValues(series, "IS", "operating_income")

    def _std(values: list) -> float:
        """변동계수(CV) 산출 — 표준편차 / 평균 (비율, 0~1)."""
        valid = [v for v in values if v is not None]
        if len(valid) < 3:
            return 0.1  # 기본값 10%
        mean = sum(valid) / len(valid)
        if abs(mean) < 1e-12:
            return 0.1
        variance = sum((v - mean) ** 2 for v in valid) / (len(valid) - 1)
        return math.sqrt(variance) / abs(mean)

    def _marginStd(revList: list, oiList: list) -> float:
        """영업이익률 표준편차 산출 (%p)."""
        margins = []
        for r, o in zip(revList, oiList):
            if r is not None and o is not None and r > 0:
                margins.append(o / r * 100)
        if len(margins) < 3:
            return 2.0  # 기본 2%p
        mean = sum(margins) / len(margins)
        variance = sum((m - mean) ** 2 for m in margins) / (len(margins) - 1)
        return math.sqrt(variance)

    return {
        "revenueCv": _std(revVals),
        "marginStd": _marginStd(revVals, oiVals),
    }


def _applyMacroShock(
    baseRevenue: float,
    baseMargin: float,
    scenario: MacroScenario,
    elasticity: SectorElasticity,
    yearIdx: int,
    baseWacc: float,
) -> tuple[float, float, float]:
    """매크로 충격을 기업 실적에 적용.

    Parameters
    ----------
    baseRevenue : float
        기준 매출 (원).
    baseMargin : float
        기준 영업이익률 (%).
    scenario : MacroScenario
        거시경제 시나리오.
    elasticity : SectorElasticity
        업종별 경기감응도.
    yearIdx : int
        시나리오 내 연도 인덱스 (0-based).
    baseWacc : float
        기준 가중평균자본비용 (%).

    Returns
    -------
    tuple[float, float, float]
        adjustedRevenue : float — 조정 매출 (원)
        adjustedMargin : float — 조정 영업이익률 (%, 하한 -50%)
        adjustedWacc : float — 조정 할인율 (%)
    """
    gdp = scenario.gdpGrowth[yearIdx]
    rate = scenario.interestRate[yearIdx]
    fx = scenario.krwUsd[yearIdx]

    # GDP 충격
    revGdpEffect = elasticity.revenueToGdp * gdp / 100

    # 환율 충격 (baseline 대비 변화율)
    fxChangePct = (fx - BASELINE_FX) / BASELINE_FX * 100
    revFxEffect = elasticity.revenueToFx * fxChangePct / 1000  # 10%당 beta 적용

    adjustedRevenue = baseRevenue * (1 + revGdpEffect + revFxEffect)

    # 마진 충격
    marginShockBps = elasticity.marginToGdp * gdp / 100
    # NIM 충격 (금융업)
    rateChange = rate - BASELINE_RATE
    nimShockBps = elasticity.nimToRate * rateChange / 100
    adjustedMargin = baseMargin + marginShockBps + nimShockBps

    # WACC 조정 (금리 변동의 50% 반영)
    adjustedWacc = baseWacc + rateChange * 0.5

    return adjustedRevenue, max(adjustedMargin, -50), adjustedWacc


# simulateScenario + simulateAllScenarios — _simScenario.py 분리 (BC re-export)
# Monte Carlo + Stress Test 분리 (BC re-export)
from dartlab.analysis.forecast._simMonteCarlo import monteCarloForecast, stressTest  # noqa: E402, F401
from dartlab.analysis.forecast._simScenario import (  # noqa: E402, F401
    simulateAllScenarios,
    simulateScenario,
)
