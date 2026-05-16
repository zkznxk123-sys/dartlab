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


# ── 시나리오 시뮬레이션 ──


def simulateScenario(
    series: dict,
    scenario: MacroScenario | str,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
    shares: int | None = None,
) -> SimulationResult:
    """단일 거시 시나리오 → 3 년 매출/영업이익/FCF/DCF 시뮬레이션.

    Capabilities:
        매크로 시나리오 (GDP/금리/환율/CPI 3 년 경로) 와 업종 탄성치를 결합
        하여 매출 → 영업이익 → FCF 시계열을 산출하고 DCF 기업가치를 계산.
        시나리오 분석의 기본 단위 (simulateAllScenarios, simulateHistorical,
        stressTest 모두 본 함수를 내부 호출).

    Args:
        series: ``finance.timeseries`` dict (BS/IS/CF 시계열).
        scenario: ``MacroScenario`` 객체 또는 프리셋 이름 (``"baseline"``,
            ``"adverse"``, ``"severely_adverse"``).
        sectorKey: WICS 업종 키. 업종별 탄성치 룩업.
        sectorParams: 업종별 파라미터 (할인율, 성장률).
        shares: 발행주식수. 주당 가치 산출용.

    Returns:
        SimulationResult dataclass:
            - ``scenarioName``/``scenarioLabel`` (str)
            - ``years`` (int): 시뮬 기간 (3 년)
            - ``revenuePath``/``operatingIncomePath``/``marginPath``/``fcfPath``
              (list[float]): 연도별 시계열
            - ``dcfValue`` (float): DCF 기업가치
            - ``perShareValue`` (float|None): 주당 가치
            - ``revenueChangePct``/``marginChangeBps`` (float): 최종 변화량
            - ``elasticityUsed`` (SectorElasticity): 적용된 탄성치
            - ``assumptions`` (dict): 가정 투명화
            - ``warnings`` (list[str]): 경고
        시나리오 매칭 실패 시 빈 path + warnings 포함 결과.

    Raises:
        없음 (내부 catch).

    Example:
        >>> from dartlab import Company
        >>> c = Company("005930")
        >>> r = simulateScenario(c.finance.timeseries, "adverse", sectorKey="IT")
        >>> r.revenuePath, r.dcfValue

    Guide:
        baseline = 매크로 변화 없음 (현재 추세 연장). adverse = 1 표준편차
        충격 (GDP -2%p, 금리 +200bp). severely_adverse = 2 표준편차.
        learnedBetas 입력 시 (simulateHistorical) 정적 탄성치 override.

    SeeAlso:
        - ``simulateAllScenarios``: 3 시나리오 일괄
        - ``simulateHistorical``: 과거 위기 재현
        - ``monteCarloForecast``: 1000 회 확률 분포
        - ``stressTest``: 극단 스트레스

    Requires:
        ``series`` 가 finance.timeseries 스키마. ``MacroScenario`` 가
        gdpGrowth/interestRate/krwUsd/cpi 3 년 list 보유.

    AIContext:
        scenarioName="알 수 없음" 결과 무시. assumptions dict 의 키-값을
        리포트에 노출하여 어떤 탄성치/할인율이 적용됐는지 투명화.

    LLM Specifications:
        AntiPatterns:
            - 단일 시나리오 결과만 인용 금지 — baseline + adverse + severe
              3 개 비교 권장.
            - revenuePath 의 절대값보다 변화율 (revenueChangePct) 이 시나리오
              간 비교에 적합.
        OutputSchema:
            SimulationResult (11 필드 dataclass).
        Prerequisites:
            series 에 IS/CF/BS 시계열 + sectorKey 적합 (없으면 default 사용).
        Freshness:
            series 의 freshness (최신 분기). MacroScenario 는 정적.
        Dataflow:
            scenario 정규화 → 업종 탄성치 룩업 → 매출 path (GDP × β) →
            영업이익 path (margin × β) → FCF (FCF/NI 비율) → DCF (할인) →
            결과 dataclass.
        TargetMarkets: KR + US (sectorKey 인자가 시장별 분기).
    """
    warnings: list[str] = []

    # 시나리오 로드
    if isinstance(scenario, str):
        sc = PRESET_SCENARIOS.get(scenario)
        if sc is None:
            return SimulationResult(
                scenarioName=scenario,
                scenarioLabel="알 수 없음",
                years=0,
                revenuePath=[],
                operatingIncomePath=[],
                marginPath=[],
                fcfPath=[],
                dcfValue=0,
                perShareValue=None,
                revenueChangePct=0,
                marginChangeBps=0,
                elasticityUsed=DEFAULT_ELASTICITY,
                warnings=[f"미지원 시나리오: {scenario}. 선택지: {', '.join(PRESET_SCENARIOS)}"],
            )
    else:
        sc = scenario

    elasticity = getElasticity(sectorKey)
    base = _extractBaseMetrics(series)
    baseWacc = sectorParams.discountRate if sectorParams else 10.0

    rev = base["revenue"]
    margin = base["margin"]
    if rev is None or rev <= 0:
        return SimulationResult(
            scenarioName=sc.name,
            scenarioLabel=sc.label,
            years=0,
            revenuePath=[],
            operatingIncomePath=[],
            marginPath=[],
            fcfPath=[],
            dcfValue=0,
            perShareValue=None,
            revenueChangePct=0,
            marginChangeBps=0,
            elasticityUsed=elasticity,
            warnings=["매출 데이터 부족"],
        )

    if margin is None:
        margin = 10.0
        warnings.append("마진 데이터 미확인 -> 10%로 가정")

    capexRatio = abs(base["capex"] or 0) / rev if rev > 0 else 0.05
    taxRate = 0.22  # 한국 법인세 기본

    # 3년 경로 시뮬레이션
    horizon = min(len(sc.gdpGrowth), 3)
    revenuePath: list[float] = []
    oiPath: list[float] = []
    marginPath: list[float] = []
    fcfPath: list[float] = []
    waccPath: list[float] = []

    prevRev = rev
    prevMargin = margin

    for yr in range(horizon):
        adjRev, adjMargin, adjWacc = _applyMacroShock(
            prevRev,
            prevMargin,
            sc,
            elasticity,
            yr,
            baseWacc,
        )
        adjOi = adjRev * adjMargin / 100
        adjFcf = adjOi * (1 - taxRate) - adjRev * capexRatio

        revenuePath.append(adjRev)
        oiPath.append(adjOi)
        marginPath.append(adjMargin)
        fcfPath.append(adjFcf)
        waccPath.append(adjWacc)

        prevRev = adjRev
        prevMargin = adjMargin

    # DCF 가치 (시나리오 경로의 FCF 합산)
    terminalGrowth = min(sectorParams.growthRate if sectorParams else 3.0, 3.0)
    lastWacc = waccPath[-1] if waccPath else baseWacc

    if lastWacc <= terminalGrowth:
        terminalGrowth = max(lastWacc - 2.0, 0.5)

    pvSum = sum(fcf / (1 + lastWacc / 100) ** (yr + 1) for yr, fcf in enumerate(fcfPath))
    terminalFcf = fcfPath[-1] if fcfPath else 0
    if terminalFcf > 0:
        tv = terminalFcf * (1 + terminalGrowth / 100) / (lastWacc / 100 - terminalGrowth / 100)
        pvTv = tv / (1 + lastWacc / 100) ** horizon
    else:
        tv = 0
        pvTv = 0
        warnings.append("FCF 음수 -> Terminal Value 미적용")

    ev = pvSum + pvTv
    netDebt = base["netDebt"] or 0
    equityValue = ev - netDebt
    perShare = equityValue / shares if shares and shares > 0 else None

    # 변화율 계산
    finalRev = revenuePath[-1] if revenuePath else rev
    revChange = (finalRev - rev) / rev * 100 if rev > 0 else 0
    marginChange = (marginPath[-1] - margin) * 100 if marginPath else 0  # bps

    return SimulationResult(
        scenarioName=sc.name,
        scenarioLabel=sc.label,
        years=horizon,
        revenuePath=revenuePath,
        operatingIncomePath=oiPath,
        marginPath=marginPath,
        fcfPath=fcfPath,
        dcfValue=ev,
        perShareValue=perShare,
        revenueChangePct=round(revChange, 1),
        marginChangeBps=round(marginChange, 0),
        elasticityUsed=elasticity,
        assumptions={
            "경기감응도(beta)": f"GDP {elasticity.revenueToGdp:.1f}, FX {elasticity.revenueToFx:.1f}",
            "업종 경기민감도": elasticity.cyclicality,
            "할인율": f"{baseWacc:.1f}% -> {lastWacc:.1f}%",
            "CapEx 비율": f"{capexRatio * 100:.1f}%",
        },
        warnings=warnings,
    )


def simulateAllScenarios(
    series: dict,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
    shares: int | None = None,
    scenarios: list[str] | None = None,
) -> dict[str, SimulationResult]:
    """모든 사전 정의 시나리오 일괄 시뮬레이션.

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
    scenarios : list[str], optional
        실행할 시나리오 키 목록. None이면 전체 프리셋.

    Returns
    -------
    dict[str, SimulationResult]
        시나리오 키 → SimulationResult 매핑.
    """
    keys = scenarios or list(PRESET_SCENARIOS.keys())
    return {
        key: simulateScenario(series, key, sectorKey, sectorParams, shares) for key in keys if key in PRESET_SCENARIOS
    }


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
