"""거시 forward 시뮬레이션 — 공개 진입(dartlab.macro.simulate).

BVAR 변수 팬 + 충격반응(IRF) + 국면경로(Hamilton 전이행렬 Markov forward)를 결정론으로 산출.
정직 척추: 안정성 미달·표본 부족은 fail-closed("표시 보류"), 넓은 밴드(파라미터 불확실성 포함),
scenario≠forecast, look-ahead 차단(asOf). 보정(coverage)은 빌드 stage 가 별도 측정·동봉.

⚠ 최상위 dartlab.simulate(회사 pro-forma 캐스케이드)와 별개 — 본 엔진은 거시 변수/국면 레벨.
"""

from __future__ import annotations

from dartlab.macro.simulate._panel import buildPanel
from dartlab.macro.simulate._types import MacroSimResult, VarSpec
from dartlab.macro.simulate.bvar import estimateBvar, maxCompanionModulus
from dartlab.macro.simulate.fan import forwardFan
from dartlab.macro.simulate.irf import impulseResponse
from dartlab.macro.simulate.regimePath import simulateRegimePath
from dartlab.macro.simulate.scenarioPath import buildScenarios

# 시장별 변수 사양(개념검증 GO 셋). policyIdx=충격 변수, gdpSeries=Hamilton 입력.
# HY스프레드(신용축)는 데이터 백필 후 편입 — 그 전엔 본 셋(원유=물가퍼즐 해소 + 장기이력).
_US_SPECS = (
    VarSpec("INDPRO", "산업생산", "logdiff100"),
    VarSpec("CPIAUCSL", "소비자물가", "logdiff100"),
    VarSpec("DCOILWTICO", "원유", "logdiff100"),
    VarSpec("FEDFUNDS", "정책금리", "level"),
    VarSpec("DGS10", "10년금리", "level"),
)
_KR_SPECS = (
    VarSpec("IPI", "산업생산", "logdiff100"),
    VarSpec("CPI", "소비자물가", "logdiff100"),
    VarSpec("DCOILWTICO", "원유", "logdiff100"),
    VarSpec("BASE_RATE", "기준금리", "level"),
    VarSpec("USDKRW", "원/달러", "logdiff100"),
)
_MARKET_SPECS = {
    "US": {"specs": _US_SPECS, "policyIdx": 3, "gdpSeries": "A191RL1Q225SBEA"},
    "KR": {"specs": _KR_SPECS, "policyIdx": 3, "gdpSeries": "GROWTH"},
}
_SEPARATION_MIN = 0.5  # Hamilton regime 분리도 게이트(regime build 와 동일).


def _regimePathBlock(gdpSeries: str, g, horizon: int) -> dict:
    """Hamilton 전이행렬 → 국면 forward. 미수렴·분리약함은 표시 보류."""
    from dartlab.macro.cycles.regimeSwitching import hamiltonRegime
    from dartlab.macro.seriesFetch import fetchSeriesList

    vals = fetchSeriesList(g, gdpSeries)
    if not vals or len(vals) < 20:
        return {"status": "표본 부족·표시 보류"}
    try:
        hr = hamiltonRegime(vals, maxIter=50)
    except (ValueError, RuntimeError) as exc:
        return {"status": f"추정 실패·표시 보류 ({type(exc).__name__})"}
    params = hr.params or {}
    muExp, muCon = params.get("mu_expansion"), params.get("mu_contraction")
    sigMax = max(params.get("sigma_expansion", 0.0), params.get("sigma_contraction", 0.0))
    sep = (muExp - muCon) / sigMax if (muExp is not None and muCon is not None and sigMax > 0) else None
    if not hr.converged:
        return {"status": "EM 미수렴·표시 보류"}
    if sep is None or sep < _SEPARATION_MIN:
        return {"status": "레짐 분리 약함·표시 보류", "separation": round(float(sep), 3) if sep is not None else None}
    # 전이확률 키 = p_stay_expansion(=p00)·p_stay_contraction(=p11). regimeLabels=(expansion, contraction).
    block = simulateRegimePath(
        params["p_stay_expansion"], params["p_stay_contraction"], hr.smoothedProbs[-1], horizon=horizon
    )
    block["history"] = [round(float(x), 4) for x in hr.smoothedProbs[-24:, 1]]
    block["separation"] = round(float(sep), 3)
    block["converged"] = True
    return block


def simulateMacro(
    market: str = "US",
    horizon: int = 12,
    *,
    asOf: str | None = None,
    lag: int = 6,
    lam: float = 0.2,
) -> MacroSimResult:
    """거시 변수·국면을 미래로 확률 시뮬 — BVAR 팬 + IRF + 국면경로.

    Capabilities:
        시장 핵심 거시 5변수 BVAR(자연켤레 Minnesota)를 추정해 향후 horizon 개월의 분위 팬
        (해석적 예측오차 분산 밴드), 정책금리 충격 IRF(재귀식별·예시), 국면 forward 경로
        (Hamilton Markov)를 *결정론*으로 산출. 거시 '예측' 축을 점추정에서 분포·경로로 확장.

    Args:
        market: 'US' | 'KR'.
        horizon: 예측 개월(기본 12).
        asOf: 기준일 'YYYY-MM-DD'. None 이면 최신. look-ahead 차단.
        lag: VAR lag 차수.
        lam: Minnesota tightness.

    Returns:
        MacroSimResult — status('ok'|'...표시 보류') · model 메타 · fan · irf · regimePath · missing.
        status≠'ok' 면 fan/irf 빈 dict. .toPayload() 로 JSON 직렬화.

    Raises:
        ValueError: 미지원 market.

    Example:
        >>> r = simulateMacro("US", horizon=12)  # doctest: +SKIP
        >>> r.status, list(r.fan)[:2]
        ('ok', ['산업생산', '소비자물가'])

    Guide:
        해석적 밴드(난수 0)라 byte 수준 결정론 — 터미널 TS 런타임이 같은 수식으로 재현(parity).
        IRF 방향부호는 재귀식별 아티팩트(price/output puzzle)라 구조 truth 아님 — caveat 동반.
        보정(coverage)은 fanCalibration 으로 측정(본 함수 미포함).

    When:
        dartlab.macro('시뮬레이션') · 터미널 전망 뷰 TS 포팅의 Python 정본·parity 기준.

    How:
        getGather(asOf) → buildPanel(월말 리샘플·변환) → estimateBvar →
        maxCompanionModulus 안정성 게이트 → forwardFan(해석적) + impulseResponse +
        Hamilton regimePath → MacroSimResult.

    Requires:
        FRED/ECOS provider 활성(getGather). market 시리즈 ≥ 10년.

    See Also:
        - dartlab.macro.forecast.analyzeForecast : 현재 침체확률 점추정
        - dartlab.macro.cycles.regimeSwitching.hamiltonRegime : 국면경로 전이행렬 원천
    """
    mk = market.upper()
    if mk not in _MARKET_SPECS:
        raise ValueError("market 은 'US' 또는 'KR' 만 지원합니다.")
    cfg = _MARKET_SPECS[mk]
    specs = cfg["specs"]

    from dartlab.macro.seriesFetch import getGather

    g = getGather(asOf)
    panel, missing = buildPanel(g, specs)
    base = {"kind": "BVAR", "lag": lag, "prior": "minnesota", "vars": [s.seriesId for s in specs]}
    if panel is None:
        return MacroSimResult(
            mk, "표본 부족·표시 보류", asOf or "", horizon, {**base, "status": "표시 보류"}, {}, {}, {}, missing
        )

    fit = estimateBvar(panel.panel, specs, p=lag, lam=lam, lastLevels=panel.lastLevels, endYm=panel.endYm)
    eig = maxCompanionModulus(fit)
    if eig >= 1.0:
        return MacroSimResult(
            mk,
            "불안정(비정상)·표시 보류",
            panel.endYm,
            horizon,
            {**base, "nObs": fit.nObs, "companionEig": round(eig, 4), "status": "표시 보류"},
            {},
            {},
            {},
            [{"id": "stability", "status": "표시 보류", "reason": f"eig {eig:.3f}>=1"}],
        )

    fan = forwardFan(fit, panel.panel, horizon=horizon)
    irf = impulseResponse(fit, horizon=24, shockVar=cfg["policyIdx"], shockSize=1.0)
    irf["shockLabel"] = "정책금리 +100bp"
    regimePath = _regimePathBlock(cfg["gdpSeries"], g, horizon)
    scenarios = buildScenarios(fit, panel.panel, cfg["policyIdx"], horizon=horizon)

    model = {**base, "nObs": fit.nObs, "companionEig": round(eig, 4), "endYm": panel.endYm, "status": "ok"}
    return MacroSimResult(mk, "ok", panel.endYm, horizon, model, fan, irf, regimePath, [], scenarios)


def analyzeSimulation(market: str = "US", **kwargs) -> dict:
    """거시 시뮬 axis 진입(dict 반환) — dartlab.macro('시뮬레이션') 디스패치용.

    simulateMacro(타입드) 의 dict wrapper. 본 함수는 6막 forecast 가족(act 6)의 *전망 시뮬*
    축. 타입드 결과·빌드 stage 는 simulateMacro 직접 사용.

    Args:
        market: 'US' | 'KR'.
        **kwargs: horizon/asOf/draws/seed/lag/lam (simulateMacro 전달).

    Returns:
        dict — MacroSimResult.toPayload() (market/status/asOf/horizon/model/fan/irf/regimePath/scenarios/missing).
    """
    return simulateMacro(market=market, **kwargs).toPayload()
