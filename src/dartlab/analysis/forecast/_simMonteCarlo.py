"""Monte Carlo + Stress Test simulation — monteCarloForecast + stressTest.

simulation.py 의 monteCarloForecast (10000 iteration 시뮬레이션) + stressTest (역사적 충격
3 종 적용) 분리. random 모듈 기반 외부 의존성 없는 순수 시뮬레이션.

simulation.py god module 분리 일환.
"""

from __future__ import annotations

import math
import random
from dataclasses import field

from dartlab.analysis.forecast._simTypes import MonteCarloResult, StressTestResult
from dartlab.core.utils.extract import getLatest, getTTM
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
    """simulation.py 의 _extractBaseMetrics lazy proxy (cycle 회피)."""
    from dartlab.analysis.forecast.simulation import _extractBaseMetrics as _ex

    return _ex(series)


def _applyMacroShock(*args, **kwargs):
    """simulation.py 의 _applyMacroShock lazy proxy."""
    from dartlab.analysis.forecast.simulation import _applyMacroShock as _ams

    return _ams(*args, **kwargs)


def _extractVolatility(series: dict) -> dict[str, float]:
    """simulation.py 의 _extractVolatility lazy proxy."""
    from dartlab.analysis.forecast.simulation import _extractVolatility as _ev

    return _ev(series)


def simulateScenario(*args, **kwargs):
    """simulation.simulateScenario lazy proxy (cycle 회피).

    Requires:
        dartlab.analysis.forecast.simulation 모듈 import 가능.

    Raises:
        없음. 본체 함수의 예외 그대로 전파.

    Example:
        >>> simulateScenario(series, "baseline")
        SimulationResult(...)
    """
    from dartlab.analysis.forecast.simulation import simulateScenario as _ss

    return _ss(*args, **kwargs)


# ── Monte Carlo 시뮬레이션 ──


def monteCarloForecast(
    series: dict,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
    shares: int | None = None,
    scenario: MacroScenario | str = "baseline",
    iterations: int = 10000,
    horizon: int = 3,
    seed: int | None = None,
) -> MonteCarloResult:
    """Monte Carlo 시뮬레이션으로 매출·이익·FCF 분포 추정.

    Capabilities:
        - 시나리오 평균 경로에 정규 노이즈 추가해 분포 산출
        - P5/P25/P50/P75/P95 백분위 + VaR95 + 상승 확률 동행

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    sectorKey : str, optional
        WICS 업종 키.
    sectorParams : SectorParams, optional
        업종별 파라미터.
    shares : int, optional
        발행주식수.
    scenario : MacroScenario | str
        기준 시나리오 (기본 "baseline").
    iterations : int
        시뮬레이션 반복 횟수 (기본 10,000).
    horizon : int
        예측 기간 (년, 기본 3).
    seed : int, optional
        난수 시드 (재현성용).

    Returns
    -------
    MonteCarloResult
        iterations : int — 실행 횟수
        scenarioName : str — 기준 시나리오명
        percentiles : dict[str, dict[str, float]] — 메트릭별 백분위 (P5/P25/P50/P75/P95)
        expectedValue : float — 기대 매출 (원)
        stdDev : float — 매출 표준편차 (원)
        var95 : float — 95% VaR 매출 (원)
        upsideProbability : float — 현재 대비 상승 확률 (%)

    Guide:
        결정론적 시뮬 결과를 확률 분포로 확장. seed 고정으로 재현 가능.

    When:
        단일 적정가가 아닌 확률 분포가 필요할 때.

    How:
        시나리오 평균 경로 산출 → Gaussian 노이즈 × iterations 반복 → 백분위.

    Requires:
        매출 시계열 존재, sectorKey (없으면 default elasticity).

    Raises:
        없음. 매출 0/None 시 빈 결과 + warnings.

    Example:
        >>> r = monteCarloForecast(series, iterations=1000, seed=42)
        >>> "매출" in r.percentiles or r.warnings
        True

    See Also:
        - stressTest : 단일 극한 시나리오
        - simulateScenario : 결정론적 시뮬

    AIContext:
        AI 답변 시 P50/P95 백분위 + 상승확률 표로 인용 — VaR 함께 표시.
    """
    if seed is not None:
        random.seed(seed)

    warnings: list[str] = []

    # 시나리오 로드
    if isinstance(scenario, str):
        sc = PRESET_SCENARIOS.get(scenario, PRESET_SCENARIOS["baseline"])
    else:
        sc = scenario

    elasticity = getElasticity(sectorKey)
    base = _extractBaseMetrics(series)
    vol = _extractVolatility(series)
    baseWacc = sectorParams.discountRate if sectorParams else 10.0

    rev = base["revenue"]
    margin = base["margin"]
    if rev is None or rev <= 0:
        return MonteCarloResult(
            iterations=iterations,
            scenarioName=sc.name,
            percentiles={},
            expectedValue=0,
            stdDev=0,
            var95=0,
            upsideProbability=0,
            warnings=["매출 데이터 부족"],
        )
    if margin is None:
        margin = 10.0

    revCv = min(vol["revenueCv"], 0.5)  # 상한 50%
    marginStd = min(vol["marginStd"], 10.0)  # 상한 10%p

    # 평균 경로 계산 (시나리오 기반)
    meanRevPath: list[float] = []
    meanMarginPath: list[float] = []
    prevR, prevM = rev, margin
    for yr in range(min(horizon, len(sc.gdpGrowth))):
        ar, am, _ = _applyMacroShock(prevR, prevM, sc, elasticity, yr, baseWacc)
        meanRevPath.append(ar)
        meanMarginPath.append(am)
        prevR, prevM = ar, am

    # Monte Carlo 실행
    finalRevenues: list[float] = []
    finalOis: list[float] = []
    finalFcfs: list[float] = []

    capexRatio = abs(base["capex"] or 0) / rev if rev > 0 else 0.05
    taxRate = 0.22

    for _ in range(iterations):
        simRev = rev
        simMargin = margin
        for yr in range(len(meanRevPath)):
            # 평균 경로에 노이즈 추가
            revNoise = random.gauss(0, revCv)
            marginNoise = random.gauss(0, marginStd)

            simRev = meanRevPath[yr] * (1 + revNoise)
            simMargin = meanMarginPath[yr] + marginNoise

        simOi = simRev * max(simMargin, -50) / 100
        simFcf = simOi * (1 - taxRate) - simRev * capexRatio

        finalRevenues.append(simRev)
        finalOis.append(simOi)
        finalFcfs.append(simFcf)

    # 백분위 산출
    def _percentiles(vals: list[float]) -> dict[str, float]:
        """P5/P25/P50/P75/P95 백분위 산출."""
        sortedVals = sorted(vals)
        n = len(sortedVals)
        return {
            "p5": sortedVals[int(n * 0.05)],
            "p25": sortedVals[int(n * 0.25)],
            "p50": sortedVals[int(n * 0.50)],
            "p75": sortedVals[int(n * 0.75)],
            "p95": sortedVals[int(n * 0.95)],
        }

    percentiles = {
        "매출": _percentiles(finalRevenues),
        "영업이익": _percentiles(finalOis),
        "FCF": _percentiles(finalFcfs),
    }

    # 통계
    meanRevFinal = sum(finalRevenues) / iterations
    stdDev = math.sqrt(sum((r - meanRevFinal) ** 2 for r in finalRevenues) / (iterations - 1))
    var95 = sorted(finalRevenues)[int(iterations * 0.05)]
    upsideProb = sum(1 for r in finalRevenues if r > rev) / iterations * 100

    if revCv >= 0.4:
        warnings.append("과거 매출 변동성 높음 -> 시뮬레이션 신뢰도 낮음")

    return MonteCarloResult(
        iterations=iterations,
        scenarioName=sc.label,
        percentiles=percentiles,
        expectedValue=meanRevFinal,
        stdDev=stdDev,
        var95=var95,
        upsideProbability=round(upsideProb, 1),
        warnings=warnings,
    )


# ── 스트레스 테스트 ──


def stressTest(
    series: dict,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
    scenario: str = "adverse",
) -> StressTestResult:
    """CCAR 스타일 스트레스 테스트 — 극한 시나리오 하 재무 건전성 평가.

    Capabilities:
        - 3 년 후 부채비율·유동비율·이자보상배율 추정
        - 생존 위험도·배당 지속성·회복 시점 자동 판정

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    sectorKey : str, optional
        WICS 업종 키.
    sectorParams : SectorParams, optional
        업종별 파라미터.
    scenario : str
        스트레스 시나리오 키 (기본 "adverse").

    Returns
    -------
    StressTestResult
        year3RevenueChange : float — 3년 후 매출 변화율 (%)
        year3MarginChange : float — 3년 후 마진 변화 (bps)
        year3DebtRatio : float | None — 3년 후 추정 부채비율 (%)
        year3CurrentRatio : float | None — 3년 후 추정 유동비율 (%)
        year3InterestCoverage : float | None — 3년 후 추정 이자보상배율 (배)
        survivalRisk : str — 생존 위험도 ("low" | "medium" | "high" | "critical")
        dividendSustainable : bool — 배당 지속 가능 여부
        recoveryTimeline : str — 회복 전망 설명

    Guide:
        Bank-style CCAR 시나리오를 비은행 회사에도 적용한 generic 스트레스.

    When:
        극한 거시 시나리오 (adverse/severelyAdverse) 하 생존 평가가 필요할 때.

    How:
        simulateScenario → base 재무 지표 → 3 년 후 비율 추정 + 위험도 점수.

    Requires:
        series 의 BS/IS/CF 와 PRESET_SCENARIOS 의 시나리오 키.

    Raises:
        없음. 데이터 부족은 None 으로 표기.

    Example:
        >>> r = stressTest(series, scenario="adverse")
        >>> r.survivalRisk in ("low", "medium", "high", "critical")
        True

    See Also:
        - monteCarloForecast : 분포 시뮬
        - simulateScenario : 시나리오 시뮬

    AIContext:
        AI 답변 시 survivalRisk + recoveryTimeline 함께 인용 — 단독 수치 인용 금지.
    """
    warnings: list[str] = []

    sim = simulateScenario(series, scenario, sectorKey, sectorParams)
    base = _extractBaseMetrics(series)

    sc = PRESET_SCENARIOS.get(scenario, PRESET_SCENARIOS["adverse"])

    # 3년 후 재무 건전성 추정
    revChange = sim.revenueChangePct
    marginChange = sim.marginChangeBps

    # 부채비율 추정: 이익 감소 -> 자본 감소 -> 부채비율 상승
    debtRatio3y = None
    if base["debtRatio"] is not None and base["totalEquity"] and base["totalEquity"] > 0:
        # 3년간 누적 이익 변화 반영
        cumProfitLoss = sum(sim.operatingIncomePath) * 0.78 if sim.operatingIncomePath else 0
        baselineProfit = (base["operatingIncome"] or 0) * 0.78 * 3
        equityChange = cumProfitLoss - baselineProfit
        newEquity = base["totalEquity"] + equityChange
        if newEquity > 0:
            debtRatio3y = round((base["totalLiabilities"] or 0) / newEquity * 100, 0)
        else:
            debtRatio3y = 9999
            warnings.append("스트레스 하 자본잠식 위험")

    # 유동비율 추정
    currentRatio3y = base["currentRatio"]
    if currentRatio3y is not None and revChange < -10:
        currentRatio3y = currentRatio3y * (1 + revChange / 100 * 0.3)  # 보수적 조정

    # 이자보상배율
    intCov3y = None
    if sim.operatingIncomePath and base["financeCosts"] and abs(base["financeCosts"]) > 0:
        intCov3y = round(sim.operatingIncomePath[-1] / abs(base["financeCosts"]), 1)

    # 배당 지속 가능성
    divSustainable = True
    if base["dividendsPaid"] and sim.fcfPath:
        finalFcf = sim.fcfPath[-1]
        divAmount = abs(base["dividendsPaid"] or 0)
        if finalFcf < divAmount:
            divSustainable = False

    # 생존 위험도 판단
    riskScore = 0
    if revChange < -20:
        riskScore += 2
    elif revChange < -10:
        riskScore += 1

    if debtRatio3y is not None and debtRatio3y > 300:
        riskScore += 2
    elif debtRatio3y is not None and debtRatio3y > 200:
        riskScore += 1

    if intCov3y is not None and intCov3y < 1:
        riskScore += 2
    elif intCov3y is not None and intCov3y < 2:
        riskScore += 1

    if not divSustainable:
        riskScore += 1

    if riskScore >= 5:
        survivalRisk = "critical"
    elif riskScore >= 3:
        survivalRisk = "high"
    elif riskScore >= 1:
        survivalRisk = "medium"
    else:
        survivalRisk = "low"

    # 회복 전망
    elasticity = getElasticity(sectorKey)
    if elasticity.cyclicality == "high":
        recovery = "V자 반등 가능 (경기민감 업종)"
    elif elasticity.cyclicality == "defensive":
        recovery = "안정적 — 충격 자체가 제한적"
    else:
        recovery = "점진적 회복 (1~2년)"

    return StressTestResult(
        scenarioName=sc.name,
        scenarioLabel=sc.label,
        year3RevenueChange=round(revChange, 1),
        year3MarginChange=round(marginChange, 0),
        year3DebtRatio=debtRatio3y,
        year3CurrentRatio=round(currentRatio3y, 0) if currentRatio3y else None,
        year3InterestCoverage=intCov3y,
        survivalRisk=survivalRisk,
        dividendSustainable=divSustainable,
        recoveryTimeline=recovery,
        warnings=warnings,
    )


__all__ = ["monteCarloForecast", "stressTest"]
