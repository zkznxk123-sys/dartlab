"""분석/forecast 시나리오 시뮬레이션 — simulation.py 에서 분리.

simulateScenario + simulateAllScenarios 본체.
"""

from __future__ import annotations

from dartlab.analysis.forecast._simTypes import SimulationResult
from dartlab.core.utils.extract import getLatest, getTTM
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


def _extractBaseMetrics(series: dict) -> dict:
    from dartlab.analysis.forecast.simulation import _extractBaseMetrics as _ex

    return _ex(series)


def _extractVolatility(series: dict) -> dict:
    from dartlab.analysis.forecast.simulation import _extractVolatility as _ex

    return _ex(series)


def _applyMacroShock(*args, **kwargs):
    from dartlab.analysis.forecast.simulation import _applyMacroShock as _ap

    return _ap(*args, **kwargs)


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
        >>> r = simulateScenario(c.panel("timeseries"), "adverse", sectorKey="IT")
        >>> r.revenuePath, r.dcfValue

    Guide:
        baseline = 매크로 변화 없음 (현재 추세 연장). adverse = 1 표준편차
        충격 (GDP -2%p, 금리 +200bp). severely_adverse = 2 표준편차.
        learnedBetas 입력 시 (simulateHistorical) 정적 탄성치 override.

    When:
        시나리오 단일 단위 시뮬레이션이 필요할 때 (다른 simulator 의 기본 단위).

    How:
        MacroScenario 정규화 → 업종 탄성치 → 매출/마진/FCF path → DCF 산출.

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

    Requires:
        PRESET_SCENARIOS 에 정의된 키 + simulateScenario 함수.

    Raises:
        없음. 키 누락은 결과에서 자동 제외.

    Example:
        >>> r = simulateAllScenarios(series)
        >>> "baseline" in r
        True
    """
    keys = scenarios or list(PRESET_SCENARIOS.keys())
    return {
        key: simulateScenario(series, key, sectorKey, sectorParams, shares) for key in keys if key in PRESET_SCENARIOS
    }
