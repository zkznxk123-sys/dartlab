"""매크로 예측 — LEI + 침체확률 + Hamilton RS + GDP Nowcasting.

투자전략 1: 금리 추이는 전기비 성장률에 의해 결정된다
투자전략 2: 주가지수는 명목 GDP증가율과 상관관계가 높다
투자전략 16: 전기비 성장률은 '선행지수 증가율+후행지수 증가율'이다

Hamilton (1989): Markov Regime Switching으로 확률적 경기국면 판별
Banbura et al. (2011): Dynamic Factor Model로 GDP 실시간 추정
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.cycles.regimeSwitching import clevelandProbit, conferenceBoardLEI, hamiltonRegime, sahmRule
from dartlab.macro.forecast.nowcast import gdpNowcast


def _fetchForecastData(market: str, asOf: str | None = None) -> dict[str, float | list | None]:
    """gather에서 LEI 구성요소 + 프로빗 입력 수집.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR").
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.

    Returns
    -------
    dict[str, float | list | None]
        US 시장:
            t10y3m : float — 10Y-3M 금리 스프레드 (%p)
            t10y3m_prev : float — 전기 값 (%p)
            awhman : float — 제조업 주당 평균근로시간 (시간)
            icsa : float — 신규 실업수당 청구건수 (건)
            acogno : float — 소비재 신규주문 (백만달러)
            napmnoi : float — ISM 신규주문 (pt)
            acdgno : float — 비국방 자본재 신규주문 (백만달러)
            permit : float — 건축허가 건수 (천건)
            sp500 : float — S&P500 지수
            m2real : float — 실질 M2 통화량
            umcsent : float — 미시간 소비자심리지수 (pt)
            fedfunds : float — 연방기금금리 (%)
            dgs10 : float — 10년 국채수익률 (%)
            *_prev : float — 각 지표의 전기값
            *_6m : float — 각 지표의 6개월 전 값
        KR 시장:
            cli : float — 경기선행지수 (pt)
            cci : float — 경기동행지수 (pt)
            cli_lag : float — 경기후행지수 (pt)
            *_prev : float — 각 지표의 전기값
    """
    from dartlab.macro.seriesFetch import fetchWithHistory, getGather

    g = getGather(asOf)
    data: dict[str, float | list | None] = {}

    if market.upper() == "US":
        for label, sid in [
            ("t10y3m", "T10Y3M"),
            ("awhman", "AWHMAN"),
            ("icsa", "ICSA"),
            ("acogno", "ACOGNO"),
            ("napmnoi", "AMTMNO"),
            ("acdgno", "ACDGNO"),
            ("permit", "PERMIT"),
            ("sp500", "SP500"),
            ("m2real", "M2REAL"),
            ("umcsent", "UMCSENT"),
            ("fedfunds", "FEDFUNDS"),
            ("dgs10", "DGS10"),
        ]:
            hist = fetchWithHistory(g, sid)
            if "current" in hist:
                data[label] = hist["current"]
            if "prev" in hist:
                data[f"{label}_prev"] = hist["prev"]
            if "6m" in hist:
                data[f"{label}_6m"] = hist["6m"]

    elif market.upper() == "KR":
        for label, sid in [("cli", "CLI"), ("cci", "CCI"), ("cli_lag", "CLI_LAG")]:
            hist = fetchWithHistory(g, sid)
            if "current" in hist:
                data[label] = hist["current"]
            if "prev" in hist:
                data[f"{label}_prev"] = hist["prev"]
            if "6m" in hist:
                data[f"{label}_6m"] = hist["6m"]

    return data


def _pctChange(current: float | None, prev: float | None) -> float | None:
    """전기대비 변화율 계산.

    Parameters
    ----------
    current : float | None
        현재 값.
    prev : float | None
        전기 값.

    Returns
    -------
    float | None
        변화율 (%). 입력이 None이거나 prev가 0이면 None.
    """
    if current is None or prev is None or prev == 0:
        return None
    return ((current - prev) / abs(prev)) * 100


def analyzeForecast(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """경제 예측 종합 분석.

    LEI 복제, Cleveland Fed 프로빗 침체확률, Sahm Rule,
    Hamilton Regime Switching, GDP Nowcasting을 종합한다.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR"). 기본 "US".
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.
    overrides : dict | None
        AI 가정 교체 (예: ``{"t10y3m": -0.5}``).

    Returns
    -------
    dict
        market : str — 시장 코드
        recessionProb : dict | None — Cleveland Fed 프로빗 침체확률 (US 전용)
            probability : float — 12개월 내 침체 확률 (0~1)
            zone : str — 위험 구간 ("low" | "elevated" | "high")
            zoneLabel : str — 한글 레이블
            spread : float — 10Y-3M 스프레드 (%p)
            description : str — 해설
        lei : dict | None — 경기선행지수 (Conference Board LEI 복제)
            level : float — LEI 수준 (pt)
            mom : float — 전월비 변화율 (%)
            mom6m : float — 6개월 연율 변화율 (%)
            signal : str — 시그널 ("expansion" | "slowdown" | "recession_warning")
            signalLabel : str — 한글 레이블
            availableComponents : int — 사용 가능 구성요소 수
            totalComponents : int — 전체 구성요소 수
            description : str — 해설
        sahmRule : dict | None — Sahm Rule 침체 판별 (US 전용)
            value : float — Sahm 값 (%p)
            triggered : bool — 0.5%p 임계값 초과 여부
            zone : str — 위험 구간
            zoneLabel : str — 한글 레이블
            description : str — 해설
        hamiltonRegime : dict | None — Hamilton Regime Switching
            currentRegime : str — 현재 레짐 ("확장" | "수축")
            currentProb : float — 현재 레짐 확률 (0~1)
            params : dict — 모형 파라미터
            converged : bool — 수렴 여부
            iterations : int — 반복 횟수
            contractionProb : float — 수축 레짐 확률 (0~1)
            description : str — 해설
        nowcast : dict | None — GDP Nowcasting (Dynamic Factor Model, US 전용)
            gdpEstimate : float — GDP 성장률 추정 (%)
            confidence : float — 신뢰도 (0~1)
            factorCurrent : float — 공통 요인 현재값
            converged : bool — 수렴 여부
            description : str — 해설
        timeseries : dict — 주요 시계열 (t10y3m, sp500, permit 등)
    """
    data = _fetchForecastData(market, asOf=asOf)
    if overrides:
        from dartlab.macro.seriesFetch import applyOverrides

        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    if market.upper() == "US":
        # Cleveland Fed 프로빗
        t10y3m = data.get("t10y3m")
        if t10y3m is not None:
            probit = clevelandProbit(t10y3m)
            result["recessionProb"] = {
                "probability": probit.probability,
                "zone": probit.zone,
                "zoneLabel": probit.zoneLabel,
                "spread": probit.spread,
                "description": probit.description,
            }
        else:
            result["recessionProb"] = None

        # LEI 복제
        components: dict[str, float | None] = {}

        # 각 구성요소 변화율 계산
        awhman = data.get("awhman")
        awhman_prev = data.get("awhman_prev")
        components["avg_weekly_hours"] = _pctChange(awhman, awhman_prev)

        icsa = data.get("icsa")
        icsa_prev = data.get("icsa_prev")
        if icsa is not None and icsa_prev is not None and icsa_prev > 0:
            components["initial_claims"] = -_pctChange(icsa, icsa_prev)  # 역수
        else:
            components["initial_claims"] = None

        components["new_orders_consumer"] = _pctChange(data.get("acogno"), data.get("acogno_prev"))

        # ISM 신규수주: 50 기준 편차
        napmnoi = data.get("napmnoi")
        components["ism_new_orders"] = napmnoi - 50 if napmnoi is not None else None

        components["new_orders_nondefense_cap"] = _pctChange(data.get("acdgno"), data.get("acdgno_prev"))
        components["building_permits"] = _pctChange(data.get("permit"), data.get("permit_prev"))
        components["sp500"] = _pctChange(data.get("sp500"), data.get("sp500_prev"))

        # leading credit: 간소화 (M2 실질 변화율로 근사)
        components["leading_credit"] = _pctChange(data.get("m2real"), data.get("m2real_prev"))

        # term spread: 10Y - FF 수준
        dgs10 = data.get("dgs10")
        ff = data.get("fedfunds")
        if dgs10 is not None and ff is not None:
            components["term_spread"] = dgs10 - ff
        else:
            components["term_spread"] = None

        components["consumer_expectations"] = _pctChange(data.get("umcsent"), data.get("umcsent_prev"))

        lei = conferenceBoardLEI(components)
        result["lei"] = {
            "level": lei.level,
            "mom": lei.mom,
            "mom6m": lei.mom6m,
            "signal": lei.signal,
            "signalLabel": lei.signalLabel,
            "availableComponents": sum(1 for v in components.values() if v is not None),
            "totalComponents": len(components),
            "description": lei.description,
        }

    elif market.upper() == "KR":
        result["recessionProb"] = None  # KR은 프로빗 미적용

        # 한국: 선행+동행+후행 조합 (전략 16)
        cli = data.get("cli")
        cli_prev = data.get("cli_prev")
        cci = data.get("cci")
        cci_prev = data.get("cci_prev")
        cli_lag = data.get("cli_lag")
        cli_lag_prev = data.get("cli_lag_prev")

        kr_forecast: dict = {}
        if cli is not None and cli_prev is not None:
            cli_mom = cli - cli_prev
            kr_forecast["cliMomentum"] = round(cli_mom, 2)
            kr_forecast["cliLevel"] = round(cli, 1)

        if cci is not None and cci_prev is not None:
            cci_mom = cci - cci_prev
            kr_forecast["cciMomentum"] = round(cci_mom, 2)

        if cli_lag is not None and cli_lag_prev is not None:
            lag_mom = cli_lag - cli_lag_prev
            kr_forecast["lagMomentum"] = round(lag_mom, 2)

        # 전략 16: 전기비 성장률 ≈ 선행 + 후행
        cli_m = kr_forecast.get("cliMomentum")
        lag_m = kr_forecast.get("lagMomentum")
        if cli_m is not None and lag_m is not None:
            growth_approx = cli_m + lag_m
            kr_forecast["growthApprox"] = round(growth_approx, 2)
            if growth_approx > 0.5:
                kr_forecast["growthSignal"] = "expanding"
                kr_forecast["growthLabel"] = "확장"
            elif growth_approx < -0.5:
                kr_forecast["growthSignal"] = "contracting"
                kr_forecast["growthLabel"] = "수축"
            else:
                kr_forecast["growthSignal"] = "stable"
                kr_forecast["growthLabel"] = "안정"

        result["lei"] = kr_forecast if kr_forecast else None

    # ── Sahm Rule ──
    from dartlab.macro.seriesFetch import collectTimeseries, fetchSeriesList, getGather

    g = getGather(asOf)
    result["sahmRule"] = None
    if market.upper() == "US":
        ur_vals = fetchSeriesList(g, "UNRATE")
        if ur_vals and len(ur_vals) >= 15:
            sr = sahmRule(ur_vals)
            result["sahmRule"] = {
                "value": sr.value,
                "triggered": sr.triggered,
                "zone": sr.zone,
                "zoneLabel": sr.zoneLabel,
                "description": sr.description,
            }

    # ── Hamilton Regime Switching ──
    result["hamiltonRegime"] = None
    gdp_id = "A191RL1Q225SBEA" if market.upper() == "US" else "GROWTH"
    gdp_vals = fetchSeriesList(g, gdp_id)
    if gdp_vals and len(gdp_vals) >= 20:
        try:
            hr = hamiltonRegime(gdp_vals, maxIter=50)
            result["hamiltonRegime"] = {
                "currentRegime": hr.regimeLabels[hr.currentRegime],
                "currentProb": hr.currentProb,
                "params": hr.params,
                "converged": hr.converged,
                "iterations": hr.iterations,
                "contractionProb": round(float(hr.smoothedProbs[-1, 1]), 4),
                "description": (
                    f"Hamilton RS: {hr.regimeLabels[hr.currentRegime]} "
                    f"({hr.currentProb:.1%}), "
                    f"침체확률 {hr.smoothedProbs[-1, 1]:.1%}"
                ),
            }
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as e:
            import logging

            logging.getLogger(__name__).warning("Hamilton RS 실패: %s", e)

    # ── GDP Nowcasting (DFM) ──
    result["nowcast"] = None
    if market.upper() == "US":
        indicator_ids = ["INDPRO", "PAYEMS", "RSAFS", "ICSA", "PERMIT", "SP500"]
        series_list = [fetchSeriesList(g, sid) for sid in indicator_ids]
        valid = [s for s in series_list if s is not None]
        if len(valid) == len(indicator_ids):
            min_len = min(len(s) for s in valid)
            if min_len >= 30:
                indicators_arr = np.column_stack([s[-min_len:] for s in valid])
                nc = gdpNowcast(indicators_arr, nFactors=1, arOrder=1, maxIter=30)
                result["nowcast"] = {
                    "gdpEstimate": nc.gdpEstimate,
                    "confidence": nc.confidence,
                    "factorCurrent": nc.factorCurrent,
                    "converged": nc.converged,
                    "description": nc.description,
                }

    # 시계열
    if market.upper() == "US":
        result["timeseries"] = collectTimeseries(g, {"t10y3m": "T10Y3M", "sp500": "SP500", "permit": "PERMIT"})
    else:
        result["timeseries"] = collectTimeseries(g, {"cli": "CLI", "cci": "CCI"})

    return result
