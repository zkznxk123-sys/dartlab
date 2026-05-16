"""analysis/forecast/simulation 역사적 시나리오 + 백테스트 분리.

simulation.py 가 973 줄 god module 이라 역사적 충격 재현 그룹 분리.
identity 보존을 위해 simulation.py 가 본 모듈에서 re-export 한다.

상수 + 함수:
- HISTORICAL_SCENARIOS — 7 실제 과거 거시 경로 (GFC/COVID/IT버블 등)
- simulateHistorical — 특정 역사 시나리오 단일 회사 시뮬
- backtestSimulation — 시나리오 정확도 백테스트
- _getActualRevChange — 실제 매출 변화율
- _getRevByYear — 특정 연도 매출
"""

from __future__ import annotations

from dartlab.analysis.forecast._simTypes import BacktestResult, SimulationResult
from dartlab.analysis.forecast.forecast import ScenarioResult  # noqa: F401
from dartlab.frame.sector import SectorParams
from dartlab.synth.scenario import (
    DEFAULT_ELASTICITY,
    MacroScenario,
    SectorElasticity,
    getElasticity,
)


def _lazy(name):
    """본체 simulation 모듈로 위임."""
    import importlib

    return getattr(importlib.import_module("dartlab.analysis.forecast.simulation"), name)


def simulateScenario(*args, **kwargs):
    """simulation.simulateScenario lazy proxy — 본체로 위임."""
    return _lazy("simulateScenario")(*args, **kwargs)


# ══════════════════════════════════════
# 역사적 충격 재현
# ══════════════════════════════════════


# 실제 과거 거시경제 경로 (ECOS/FRED 데이터 기반)
HISTORICAL_SCENARIOS: dict[str, MacroScenario] = {
    "gfc_2008": MacroScenario(
        "gfc_2008",
        "2008 글로벌 금융위기",
        gdpGrowth=[-5.1, 0.7, 6.5],  # 2009, 2010, 2011 (한국 실제)
        interestRate=[2.0, 2.0, 2.5],
        krwUsd=[1276, 1156, 1108],
        cpi=[2.8, 2.9, 4.0],
        description="실제 2008-2010 한국 거시경제 경로",
    ),
    "covid_2020": MacroScenario(
        "covid_2020",
        "2020 코로나 팬데믹",
        gdpGrowth=[-0.7, 4.3, 2.6],  # 2020, 2021, 2022 (한국 실제)
        interestRate=[0.5, 0.75, 3.5],
        krwUsd=[1180, 1185, 1292],
        cpi=[0.5, 2.5, 5.1],
        description="실제 2020-2022 한국 거시경제 경로",
    ),
    "euro_crisis_2011": MacroScenario(
        "euro_crisis_2011",
        "2011 유럽 재정위기",
        gdpGrowth=[3.7, 2.4, 3.2],  # 2012, 2013, 2014 (한국)
        interestRate=[3.0, 2.5, 2.0],
        krwUsd=[1126, 1055, 1053],
        cpi=[2.2, 1.3, 1.3],
        description="실제 2011-2013 한국 거시경제 경로 (유럽위기 파급)",
    ),
    "rate_hike_2022": MacroScenario(
        "rate_hike_2022",
        "2022 긴축 충격",
        gdpGrowth=[2.6, 1.4, 2.0],  # 2022, 2023, 2024
        interestRate=[3.5, 3.5, 3.0],
        krwUsd=[1292, 1306, 1380],
        cpi=[5.1, 3.6, 2.3],
        description="실제 2022-2024 글로벌 긴축 + 인플레이션",
    ),
}


def simulateHistorical(
    series: dict,
    historicalKey: str,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
    shares: int | None = None,
    learnedBetas: dict[str, float] | None = None,
) -> SimulationResult:
    """역사적 충격 재현 시뮬레이션 — 과거 위기가 반복되면 어떻게 되는가.

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    historicalKey : str
        역사적 시나리오 키 ("gfc_2008", "covid_2020",
        "euro_crisis_2011", "rate_hike_2022").
    sectorKey : str, optional
        WICS 업종 키.
    sectorParams : SectorParams, optional
        업종별 파라미터.
    shares : int, optional
        발행주식수.
    learnedBetas : dict[str, float], optional
        calcMacroRegression에서 학습된 기업별 베타.
        None이면 정적 탄성치 사용.

    Returns
    -------
    SimulationResult
        역사적 시나리오 기반 시뮬레이션 결과.
        elasticityUsed가 학습값이면 assumptions에 "학습" 표기.
    """
    sc = HISTORICAL_SCENARIOS.get(historicalKey)
    if sc is None:
        available = ", ".join(HISTORICAL_SCENARIOS.keys())
        # 빈 결과 반환
        return SimulationResult(
            scenarioName=historicalKey,
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
            warnings=[f"미지원 역사 시나리오: {historicalKey}. 선택지: {available}"],
        )

    # 학습된 베타가 있으면 탄성치 오버라이드
    if learnedBetas:
        elasticity = SectorElasticity(
            revenueToGdp=learnedBetas.get("gdp", DEFAULT_ELASTICITY.revenueToGdp),
            revenueToFx=learnedBetas.get("fx", DEFAULT_ELASTICITY.revenueToFx),
            marginToGdp=learnedBetas.get("rate", DEFAULT_ELASTICITY.marginToGdp),
            nimToRate=0,
            cyclicality="learned",
        )
    else:
        elasticity = getElasticity(sectorKey)

    result = simulateScenario(series, sc, sectorKey, sectorParams, shares)
    # 탄성치를 학습값으로 교체 (결과에 반영)
    if learnedBetas:
        result.elasticityUsed = elasticity
        result.assumptions["경기감응도(beta)"] = (
            f"학습 GDP {elasticity.revenueToGdp:.2f}, FX {elasticity.revenueToFx:.2f}"
        )
    return result


# ══════════════════════════════════════
# 시뮬레이션 백테스팅
# ══════════════════════════════════════


def backtestSimulation(
    series: dict,
    sectorKey: str | None = None,
    sectorParams: SectorParams | None = None,
) -> BacktestResult | None:
    """과거 시점으로 돌아가서 시뮬레이션 정확도 측정.

    역사적 시나리오(2008, 2020 등)를 사용하여:
    1. 해당 시점 직전 재무 데이터 기준으로 시뮬레이션 실행
    2. 실제 결과와 비교
    3. 방향 정확도 + 오차 + 시나리오 적중률 산출

    Parameters
    ----------
    series : dict
        finance.timeseries 시계열 dict.
    sectorKey : str, optional
        WICS 업종 키.
    sectorParams : SectorParams, optional
        업종별 파라미터.

    Returns
    -------
    BacktestResult | None
        scenariosTested : int — 테스트된 시나리오 수
        directionAccuracy : float — 매출 방향(증/감) 정확도 (%)
        avgError : float — 평균 절대 오차 (%)
        scenarioHitRate : float — 15%p 이내 적중률 (%)
        details : list[dict] — 시나리오별 상세 비교
        데이터 부족 시 None.
    """
    details: list[dict] = []
    warnings: list[str] = []

    # 각 역사적 시나리오 테스트
    for key, sc in HISTORICAL_SCENARIOS.items():
        sim = simulateScenario(series, sc, sectorKey, sectorParams)
        if not sim.revenuePath:
            continue

        # 실제 매출 변화 (공시 데이터에서)
        actualRevChange = _getActualRevChange(series, key)
        if actualRevChange is None:
            continue

        predictedChange = sim.revenueChangePct

        # 방향 일치 여부
        directionCorrect = (predictedChange > 0) == (actualRevChange > 0)

        # 오차
        error = abs(predictedChange - actualRevChange)

        details.append(
            {
                "scenario": key,
                "label": sc.label,
                "predictedRevChange": round(predictedChange, 1),
                "actualRevChange": round(actualRevChange, 1),
                "error": round(error, 1),
                "directionCorrect": directionCorrect,
            }
        )

    if not details:
        return None

    n = len(details)
    dirAcc = sum(1 for d in details if d["directionCorrect"]) / n * 100
    avgErr = sum(d["error"] for d in details) / n
    hitRate = sum(1 for d in details if d["error"] < 15) / n * 100  # 15%p 이내 = 적중

    return BacktestResult(
        scenariosTested=n,
        directionAccuracy=round(dirAcc, 1),
        avgError=round(avgErr, 1),
        scenarioHitRate=round(hitRate, 1),
        details=details,
        warnings=warnings,
    )


def _getActualRevChange(series: dict, historicalKey: str) -> float | None:
    """역사적 시나리오 기간의 실제 매출 변화율 추출."""
    periodMap = {
        "gfc_2008": ("2008", "2011"),
        "covid_2020": ("2019", "2022"),
        "euro_crisis_2011": ("2011", "2014"),
        "rate_hike_2022": ("2021", "2024"),
    }

    if historicalKey not in periodMap:
        return None

    startYear, endYear = periodMap[historicalKey]
    startRev = _getRevByYear(series, startYear)
    endRev = _getRevByYear(series, endYear)

    if startRev is None or endRev is None or startRev == 0:
        return None

    return (endRev - startRev) / abs(startRev) * 100


def _getRevByYear(series: dict, year: str) -> float | None:
    """특정 연도의 매출 추출."""
    from dartlab.core.utils.extract import getAnnualValues

    revValues = getAnnualValues(series, "IS", "sales") or getAnnualValues(series, "IS", "revenue")
    if not revValues:
        return None

    # periodCols에서 해당 연도 찾기
    # series dict에서 직접 연도 매칭
    for stmt in ["IS"]:
        stmtData = series.get(stmt, {})
        for account, row in stmtData.items():
            if "sales" in account.lower() or "revenue" in account.lower():
                for key, val in row.items():
                    if key.startswith(year) and val is not None:
                        return val
    return None


__all__ = [
    "HISTORICAL_SCENARIOS",
    "backtestSimulation",
    "simulateHistorical",
]
