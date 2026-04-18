"""매크로 위기 감지 — Credit-to-GDP Gap + GHS 위기예측 + 침체 대시보드.

투자전략 32: 신용스프레드는 곧 설비투자조정압력이다
투자전략 33: 공급과잉은 대부분 도산을 수반한다
투자전략 35: 국내 신용위험은 소비자물가상승률과 상관관계가 높다
투자전략 38: 금융시장 위험이 커지면 달러화는 상승한다
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

from dartlab.core.finance.crisisDetector import (
    creditToGDPGap,
    dalioDebtCyclePhase,
    dalioPolicyLeverStatus,
    fisherDebtDeflation,
    ghsCrisisScore,
    kooBalanceSheetRecession,
    krHousingFinancialStress,
    minskyPhase,
    recessionDashboard,
)
from dartlab.core.finance.liquidity import capexPressure
from dartlab.macro._helpers import get_gather


def _frozen_to_dict(obj) -> dict | None:
    """frozen dataclass → dict 변환. None이면 None 반환.

    Parameters
    ----------
    obj : frozen dataclass | None
        변환할 frozen dataclass 인스턴스. None이면 그대로 반환.

    Returns
    -------
    dict | None
        dataclass 필드를 키로 가진 dict.
        입력이 None이면 None.
    """
    if obj is None:
        return None
    from dataclasses import asdict

    return asdict(obj)


def _fetch_crisis_data(market: str, as_of: str | None = None) -> dict[str, float | list | None]:
    """gather에서 위기 감지 지표 수집.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR").
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.

    Returns
    -------
    dict[str, float | list | None]
        credit_gdp_series : list[float] — Credit/GDP 비율 시계열 (%)
        sp500_3y_return : float — S&P500 3년 수익률 (%)
        vix : float — VIX 지수 (pt)
        dxy_current : float — 달러인덱스 현재값
        dxy_3m_ago : float — 달러인덱스 3개월 전 값
        hy_series : list[float] — HY 스프레드 시계열 (bps)
        hy_current : float — HY 스프레드 현재값 (bps)
        cpi_yoy : float — CPI YoY 변화율 (%, KR 전용)
        apt_yoy : float — 아파트 가격 YoY 변화율 (%, KR 전용)
        private_saving : float — 민간 저축 (US, 십억달러)
        private_investment : float — 민간 투자 (US, 십억달러)
        gdp_level : float — GDP 수준 (US, 십억달러)
        fed_funds : float — 연방기금금리 (US, %)
        dsr : float — 부채서비스비율 (US, %)
        npl : float — 부실채권비율 (US, %)
        us_cpi_yoy : float — 미국 CPI YoY (%)
        public_debt_to_gdp : float — 공공부채/GDP (%)
        gdp_growth : float — 실질GDP 성장률 (%)
        real_rate : float — 10Y TIPS 실질금리 (%)
        debt_service_yoy : float — 부채서비스율 전년 대비 변화 (%p)
        total_debt_to_gdp : float — 총부채/GDP (%)
    """
    from dartlab.macro._helpers import fetch_latest, fetch_series_list, fetch_yoy

    g = get_gather(as_of)
    data: dict[str, float | list | None] = {}

    if market.upper() == "US":
        # HY 시계열 (bps 변환)
        hy_list = fetch_series_list(g, "BAMLH0A0HYM2")
        if hy_list:
            data["hy_series"] = [v * 100 for v in hy_list]
            data["hy_current"] = hy_list[-1] * 100

        # S&P500 3년 수익률
        sp_list = fetch_series_list(g, "SP500")
        if sp_list and len(sp_list) > 750:
            if sp_list[-750] > 0:
                data["sp500_3y_return"] = ((sp_list[-1] / sp_list[-750]) - 1) * 100

        data["vix"] = fetch_latest(g, "VIXCLS")

        # 달러인덱스
        dxy_list = fetch_series_list(g, "DTWEXBGS")
        if dxy_list and len(dxy_list) > 60:
            data["dxy_current"] = dxy_list[-1]
            data["dxy_3m_ago"] = dxy_list[-60]

        # Credit-to-GDP
        credit_list = fetch_series_list(g, "TCMDO")
        gdp_list = fetch_series_list(g, "GDP")
        if credit_list and gdp_list:
            min_len = min(len(credit_list), len(gdp_list))
            ratios = [credit_list[i] / gdp_list[i] * 100 for i in range(min_len) if gdp_list[i] > 0]
            if ratios:
                data["credit_gdp_series"] = ratios

    elif market.upper() == "KR":
        credit_list = fetch_series_list(g, "CREDIT_TOTAL")
        gdp_list = fetch_series_list(g, "GDP")
        if credit_list and gdp_list:
            min_len = min(len(credit_list), len(gdp_list))
            ratios = [credit_list[i] / gdp_list[i] * 100 for i in range(min_len) if gdp_list[i] > 0]
            if ratios:
                data["credit_gdp_series"] = ratios

        data["cpi_yoy"] = fetch_yoy(g, "CPI")
        data["apt_yoy"] = fetch_yoy(g, "APT_PRICE")

    # Koo BSR (US)
    if market.upper() == "US":
        for label, sid in [
            ("private_saving", "W987RC1Q027SBEA"),
            ("private_investment", "GPDI"),
            ("gdp_level", "GDP"),
            ("fed_funds", "FEDFUNDS"),
            ("dsr", "TDSP"),
            ("npl", "DRSFRMACBS"),
        ]:
            data[label] = fetch_latest(g, sid)
        data["us_cpi_yoy"] = fetch_yoy(g, "CPIAUCSL")

        # Dalio 부채사이클 기반지표 (Big Debt Crises Part 1)
        # 공공부채/GDP, 실질GDP 성장률, 10Y TIPS (실질금리)
        data["public_debt_to_gdp"] = fetch_latest(g, "GFDEGDQ188S")
        data["gdp_growth"] = fetch_latest(g, "A191RL1Q225SBEA")
        data["real_rate"] = fetch_latest(g, "DFII10")

        # 부채서비스율 YoY 변화 — TDSP 시계열에서 4분기 diff
        tdsp_list = fetch_series_list(g, "TDSP")
        if tdsp_list and len(tdsp_list) >= 5:
            data["debt_service_yoy"] = tdsp_list[-1] - tdsp_list[-5]

        # 총부채/GDP (TCMDO / GDP) — credit_gdp_series 의 최신값 재사용
        if data.get("credit_gdp_series"):
            data["total_debt_to_gdp"] = data["credit_gdp_series"][-1]

    return {k: v for k, v in data.items() if v is not None}


def analyze_crisis(*, market: str = "US", as_of: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """위기 감지 종합 분석.

    Credit-to-GDP Gap, GHS 위기점수, 설비투자 압력, 침체 대시보드 등
    위기 관련 지표를 종합 산출한다.

    Parameters
    ----------
    market : str
        시장 코드 ("US" | "KR"). 기본 "US".
    as_of : str | None
        기준일 (YYYY-MM-DD). None이면 최신.
    overrides : dict | None
        AI 가정 교체 (예: ``{"vix": 30}``).
    **kwargs
        probitProb : float — 프로빗 침체확률 (summary에서 전달)
        leiSignal : str — LEI 시그널 (summary에서 전달)
        ismLevel : float — ISM PMI 수준 (summary에서 전달)
        realRate : float — 실질금리 (%)

    Returns
    -------
    dict
        market : str — 시장 코드
        creditGap : dict | None — Credit-to-GDP Gap 분석
            gap : float — 갭 (%p)
            trend : float — 추세선 (%)
            actual : float — 실제 비율 (%)
            zone : str — 위험 구간 ("normal" | "warning" | "danger")
            zoneLabel : str — 위험 구간 한글 레이블
            ccybBuffer : float — 경기대응 완충자본 (%)
            description : str — 해설
        ghsScore : dict | None — GHS 위기예측 점수
            score : float — 위기 점수 (점, 0~1)
            zone : str — 위험 구간
            zoneLabel : str — 위험 구간 한글 레이블
            components : dict — 구성요소별 기여
            crisisProb : float — 위기 확률 (%)
            description : str — 해설
            regime : str — 레짐 코드
            regimeLabel : str — 레짐 한글 레이블
        capexPressure : dict | None — 설비투자 조정 압력
            pressure : str — 압력 코드
            pressureLabel : str — 압력 한글 레이블
            spreadLevel : float — HY 스프레드 수준 (bps)
            spreadChange : float — HY 스프레드 변화 (bps)
            description : str — 해설
        dollarSafeHaven : dict | None — 달러 안전자산 효과
            status : str — 상태 ("active" | "mild" | "inactive")
            statusLabel : str — 한글 레이블
            vix : float — VIX (pt)
            dxyChange3m : float — 달러인덱스 3개월 변화율 (%)
            description : str — 해설
        historicalContext : dict | None — 역사적 맥락 (US 전용)
        recessionDashboard : dict — 침체 대시보드
            composite : float — 종합 점수 (점, 0~1)
            zone : str — 위험 구간
            zoneLabel : str — 한글 레이블
            components : dict — 구성 지표
            historicalMatch : str | None — 역사적 유사 사례
            historicalFacts : dict | None — 역사적 맥락
            description : str — 해설
        minskyPhase : dict | None — Minsky 5단계 분류
            phase : int — 단계 (1~5)
            phaseLabel : str — 단계 한글명
            confidence : float — 신뢰도 (0~1)
            signals : list[str] — 근거 시그널
            description : str — 해설
        debtCyclePhase : dict | None — Dalio 부채사이클 단계 (US 전용)
        policyLeverStatus : dict | None — Dalio 정책 4 레버 소진도 (US 전용)
        dalioCaseMatch : list[dict] | None — Dalio Part 2 상세 사례 매칭
        dalio48Match : list[dict] | None — Dalio Part 3 48 사례 매칭
        crisisType : dict | None — R&R 위기 유형 분류
        rrMatch : list[dict] | None — R&R 역사적 매칭
        kooRecession : dict | None — Koo 대차대조표 불황 (US 전용)
        fisherDeflation : dict | None — Fisher 부채디플레이션 (US 전용)
        krHousingStress : dict | None — 한국 부동산-금융 스트레스 (KR 전용)
        krCreditRisk : dict | None — 한국 신용위험 ↔ CPI (KR 전용)
        excessBondPremium : dict | None — 초과채권프리미엄 (Gilchrist-Zakrajsek)
        creditCycle : dict | None — Verdad 신용사이클 4단계
        timeseries : dict — 주요 시계열 (hy_spread, vix, dxy)
    """
    data = _fetch_crisis_data(market, as_of=as_of)
    if overrides:
        from dartlab.macro._helpers import apply_overrides

        data = apply_overrides(data, overrides)
    result: dict = {"market": market.upper()}

    # Credit-to-GDP Gap
    credit_gdp_series = data.get("credit_gdp_series")
    if credit_gdp_series and len(credit_gdp_series) >= 4:
        gap_result = creditToGDPGap(credit_gdp_series)
        result["creditGap"] = {
            "gap": gap_result.gap,
            "trend": gap_result.trend,
            "actual": gap_result.actual,
            "zone": gap_result.zone,
            "zoneLabel": gap_result.zoneLabel,
            "ccybBuffer": gap_result.ccybBuffer,
            "description": gap_result.description,
        }
        credit_gap_val = gap_result.gap
    else:
        result["creditGap"] = None
        credit_gap_val = None

    # GHS 위기 점수
    sp500_3y = data.get("sp500_3y_return")
    if credit_gdp_series and sp500_3y is not None:
        # 3년 신용 변화
        if len(credit_gdp_series) >= 12:  # 분기 데이터 3년
            credit_3y = credit_gdp_series[-1] - credit_gdp_series[-12]
        elif len(credit_gdp_series) >= 4:
            credit_3y = credit_gdp_series[-1] - credit_gdp_series[0]
        else:
            credit_3y = 0

        ghs = ghsCrisisScore(credit_3y, sp500_3y, realRate=kwargs.get("realRate"))
        result["ghsScore"] = {
            "score": ghs.score,
            "zone": ghs.zone,
            "zoneLabel": ghs.zoneLabel,
            "components": ghs.components,
            "crisisProb": ghs.crisisProb,
            "description": ghs.description,
            "regime": ghs.regime,
            "regimeLabel": ghs.regimeLabel,
        }
    else:
        result["ghsScore"] = None

    # 설비투자 압력 (전략 32)
    hy_series = data.get("hy_series")
    hy_current = data.get("hy_current")
    if hy_current is not None and isinstance(hy_series, list) and len(hy_series) > 60:
        hy_3m_ago = hy_series[-60]
        hy_change = hy_current - hy_3m_ago
        capex = capexPressure(hy_current, hy_change)
        result["capexPressure"] = {
            "pressure": capex.pressure,
            "pressureLabel": capex.pressureLabel,
            "spreadLevel": capex.spreadLevel,
            "spreadChange": capex.spreadChange,
            "description": capex.description,
        }
    else:
        result["capexPressure"] = None

    # 달러 안전자산 효과 (전략 38)
    vix = data.get("vix")
    dxy_current = data.get("dxy_current")
    dxy_3m = data.get("dxy_3m_ago")
    if vix is not None and dxy_current is not None and dxy_3m is not None and dxy_3m > 0:
        dxy_change = ((dxy_current / dxy_3m) - 1) * 100
        if vix > 25 and dxy_change > 2:
            safe_haven = "active"
            safe_label = "활성"
            desc = f"VIX {vix:.1f} + 달러 {dxy_change:+.1f}% — 안전자산 수요로 달러 강세"
        elif vix > 20:
            safe_haven = "mild"
            safe_label = "경미"
            desc = f"VIX {vix:.1f} + 달러 {dxy_change:+.1f}% — 약한 안전자산 효과"
        else:
            safe_haven = "inactive"
            safe_label = "비활성"
            desc = f"VIX {vix:.1f} — 금융위험 낮음, 달러 안전자산 효과 없음"
        result["dollarSafeHaven"] = {
            "status": safe_haven,
            "statusLabel": safe_label,
            "vix": round(vix, 1),
            "dxyChange3m": round(dxy_change, 1),
            "description": desc,
        }
    else:
        result["dollarSafeHaven"] = None

    # ── 역사적 맥락 (L0 순수함수) ──
    result["historicalContext"] = None
    if market.upper() == "US":
        try:
            from dartlab.core.finance.historicalContext import buildHistoricalContext
            from dartlab.macro._helpers import fetch_monthly_dict

            g_hist = get_gather(as_of)
            hist_data: dict = {}
            for key, sid in [
                ("hy_spread", "BAMLH0A0HYM2"),
                ("spread_10y3m", "T10Y3M"),
                ("spread_10y2y", "T10Y2Y"),
                ("unrate", "UNRATE"),
                ("cpi_raw", "CPIAUCSL"),
                ("indpro", "INDPRO"),
                ("vix", "VIXCLS"),
                ("nfci", "NFCI"),
                ("fedfunds", "FEDFUNDS"),
            ]:
                md = fetch_monthly_dict(g_hist, sid)
                if md:
                    hist_data[key] = md

            if hist_data:
                hc = buildHistoricalContext(hist_data)
                result["historicalContext"] = {
                    # 위기
                    "hySpike": _frozen_to_dict(hc.hySpike),
                    "yieldCurveInversion": _frozen_to_dict(hc.yieldCurveInversion),
                    "unemploymentBounce": _frozen_to_dict(hc.unemploymentBounce),
                    "cpiAcceleration": hc.cpiAcceleration,
                    "simultaneousWarnings": _frozen_to_dict(hc.simultaneousWarnings),
                    # 호황
                    "bullishSignals": _frozen_to_dict(hc.bullishSignals),
                    "hyCompression": _frozen_to_dict(hc.hyCompression),
                    # 역사적 사건
                    "historicalEvents": [_frozen_to_dict(e) for e in hc.historicalEvents]
                    if hc.historicalEvents
                    else None,
                    # 종합
                    "riskLevel": hc.riskLevel,
                    "riskLabel": hc.riskLabel,
                    "opportunityLevel": hc.opportunityLevel,
                    "opportunityLabel": hc.opportunityLabel,
                    # 다음 장
                    "suggestedScenario": hc.suggestedScenario,
                    "suggestedScenarioReason": hc.suggestedScenarioReason,
                    "description": hc.description,
                }
        except (ImportError, KeyError, ValueError, TypeError) as e:
            log.debug("역사적 맥락 계산 실패: %s", e)

    # 침체 대시보드 (다른 축 결과 필요 — 독립 실행 시 가용 데이터만 사용)
    probit_prob = kwargs.get("probitProb")
    lei_signal = kwargs.get("leiSignal")
    ism_level = kwargs.get("ismLevel")

    dashboard = recessionDashboard(
        probitProb=probit_prob,
        leiSignal=lei_signal,
        ismLevel=ism_level,
        creditGap=credit_gap_val,
        hySpread=hy_current,
    )
    result["recessionDashboard"] = {
        "composite": dashboard.composite,
        "zone": dashboard.zone,
        "zoneLabel": dashboard.zoneLabel,
        "components": dashboard.components,
        "historicalMatch": dashboard.historicalMatch,
        "historicalFacts": result.get("historicalContext"),
        "description": dashboard.description,
    }

    # ── Minsky 5단계 ──
    result["minskyPhase"] = None
    try:
        dxy_chg_val = None
        if dxy_current is not None and data.get("dxy_3m_ago") is not None:
            d3m = data["dxy_3m_ago"]
            if d3m > 0:
                dxy_chg_val = ((dxy_current / d3m) - 1) * 100
        mk = minskyPhase(
            creditGap=credit_gap_val,
            assetReturn3y=data.get("sp500_3y_return"),
            hySpread=hy_current,
            vix=vix,
            dxyChange=dxy_chg_val,
        )
        result["minskyPhase"] = {
            "phase": mk.phase,
            "phaseLabel": mk.phaseLabel,
            "confidence": mk.confidence,
            "signals": mk.signals,
            "description": mk.description,
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # ── Dalio Part 2: detail case matching (Weimar/GreatDepression/Subprime) ──
    result["dalioCaseMatch"] = None
    try:
        from dartlab.core.finance.dalioCaseMatch import matchDalioDetailCase

        case_state = {
            "totalDebtToGdp": data.get("total_debt_to_gdp"),
            "creditGap": credit_gap_val,
            "realRate": data.get("real_rate"),
            "gdpGrowth": data.get("gdp_growth"),
            "debtServiceYoY": data.get("debt_service_yoy"),
        }
        if any(v is not None for v in case_state.values()):
            result["dalioCaseMatch"] = matchDalioDetailCase(case_state, topK=3)
    except (ImportError, KeyError, ValueError, TypeError):
        pass

    # ── Dalio Part 3: 48-case compendium matching ──
    result["dalio48Match"] = None
    try:
        from dartlab.core.finance.dalio48Match import match48Cases

        state_48 = {
            "peakDebtToGdp": data.get("total_debt_to_gdp"),
            "peakCreditGap": credit_gap_val,
            "troughRealRate": data.get("real_rate"),
            "troughGdpGrowth": data.get("gdp_growth"),
        }
        if any(v is not None for v in state_48.values()):
            result["dalio48Match"] = match48Cases(state_48, topK=5)
    except (ImportError, KeyError, ValueError, TypeError):
        pass

    # ── R&R 위기 유형 분류 + 역사 매칭 ──
    result["crisisType"] = None
    result["rrMatch"] = None
    try:
        from dartlab.core.finance.rrCrisisDB import classifyCrisisType, matchRrHistorical

        ct = classifyCrisisType(
            hySpread=hy_current,
            npl=data.get("npl"),
            fxDepreciationYoy=kwargs.get("fxDepreciationYoy"),
            inflationYoy=data.get("us_cpi_yoy") or data.get("cpi_yoy"),
            sovereignSpread=kwargs.get("sovereignSpread"),
            gdpGrowth=data.get("gdp_growth"),
        )
        result["crisisType"] = {
            "activeTypes": ct["activeTypes"],
            "dominantType": ct["dominantType"],
            "isTripleCrisis": ct["isTripleCrisis"],
            "signals": ct["signals"],
        }
        if ct["activeTypes"]:
            result["rrMatch"] = matchRrHistorical(
                ct["activeTypes"],
                country=market.upper() if market.upper() in ("US", "KR") else None,
                topK=3,
            )
    except (ImportError, KeyError, ValueError, TypeError):
        pass

    # ── Dalio 부채사이클 + 정책 4 레버 ──
    # Big Debt Crises Part 1 — 6 phase enum + 4 lever 소진도
    # 입력: kwargs 우선, 없으면 _fetch_crisis_data 에서 자동 주입
    result["debtCyclePhase"] = None
    result["policyLeverStatus"] = None
    try:
        dp = dalioDebtCyclePhase(
            totalDebtToGdp=kwargs.get("totalDebtToGdp") or data.get("total_debt_to_gdp"),
            debtServiceYoY=kwargs.get("debtServiceYoY") or data.get("debt_service_yoy"),
            creditGap=credit_gap_val,
            realRate=kwargs.get("realRate") or data.get("real_rate"),
            gdpGrowth=kwargs.get("gdpGrowth") or data.get("gdp_growth"),
        )
        result["debtCyclePhase"] = {
            "phase": dp.phase,
            "phaseLabel": dp.phaseLabel,
            "signals": list(dp.signals),
            "description": dp.description,
        }

        pl = dalioPolicyLeverStatus(
            policyRate=kwargs.get("policyRate") or data.get("fed_funds"),
            publicDebtToGdp=kwargs.get("publicDebtToGdp") or data.get("public_debt_to_gdp"),
            creditGap=credit_gap_val,
            fxFlexibility=kwargs.get("fxFlexibility"),
        )
        result["policyLeverStatus"] = {
            "monetary": pl.monetary,
            "fiscal": pl.fiscal,
            "credit": pl.credit,
            "fx": pl.fx,
            "exhaustionScore": pl.exhaustionScore,
            "signals": list(pl.signals),
        }
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # ── Koo Balance Sheet Recession (US) ──
    result["kooRecession"] = None
    if market.upper() == "US":
        try:
            saving = data.get("private_saving")
            investment = data.get("private_investment")
            gdp_level = data.get("gdp_level")
            ff = data.get("fed_funds")
            if saving is not None and investment is not None and gdp_level is not None and ff is not None:
                koo = kooBalanceSheetRecession(saving, investment, gdp_level, ff)
                result["kooRecession"] = {
                    "privateSurplus": koo.privateSurplus,
                    "policyRate": koo.policyRate,
                    "isBSR": koo.isBSR,
                    "description": koo.description,
                }
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    # ── Fisher Debt-Deflation (US) ──
    result["fisherDeflation"] = None
    if market.upper() == "US":
        try:
            dsr = data.get("dsr")
            us_cpi = data.get("us_cpi_yoy")
            npl = data.get("npl")
            if dsr is not None and us_cpi is not None:
                fisher = fisherDebtDeflation(dsr, us_cpi, npl)
                result["fisherDeflation"] = {
                    "dsr": fisher.dsr,
                    "nplRate": fisher.nplRate,
                    "cpiYoy": fisher.cpiYoy,
                    "risk": fisher.risk,
                    "riskLabel": fisher.riskLabel,
                    "description": fisher.description,
                }
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    # ── KR 부동산-금융 스트레스 ──
    if market.upper() == "KR":
        try:
            apt_yoy = data.get("apt_yoy")
            if apt_yoy is not None:
                hs = krHousingFinancialStress(apt_yoy)
                result["krHousingStress"] = {
                    "housePriceYoy": hs.housePriceYoy,
                    "stress": hs.stress,
                    "stressLabel": hs.stressLabel,
                    "description": hs.description,
                }
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    # 한국 신용위험 ↔ CPI (전략 35)
    if market.upper() == "KR":
        cpi_yoy = data.get("cpi_yoy")
        if cpi_yoy is not None:
            if cpi_yoy > 4:
                cr_signal = "CPI 상승률 높음 → 신용위험 확대 경계"
            elif cpi_yoy > 2:
                cr_signal = "CPI 안정 → 신용위험 보통"
            else:
                cr_signal = "CPI 둔화 → 신용위험 낮음"
            result["krCreditRisk"] = {
                "cpiYoy": round(cpi_yoy, 1),
                "signal": cr_signal,
            }

    # ── Excess Bond Premium — Gilchrist & Zakrajšek (2012) AER ──
    result["excessBondPremium"] = None
    try:
        from dartlab.core.finance.excessBondPremium import approximateEBP, classifyEBP
        from dartlab.macro._helpers import fetch_latest as _fl
        from dartlab.macro._helpers import get_gather as _gg

        _g = _gg(as_of)
        _hy = _fl(_g, "BAMLH0A0HYM2")
        _baa_aaa = _fl(_g, "BAA10Y")  # BAA-AAA spread (부도 프리미엄 근사)
        if _hy is not None and _baa_aaa is not None:
            hy_bp = _hy * 100  # % → bp
            # BAA-AAA spread를 기대부도프리미엄 근사치로 사용 (스케일: ×1.5)
            default_proxy = _baa_aaa * 150  # %p → bp, 스케일 조정
            ebp_val = approximateEBP(hy_bp, default_proxy)
            result["excessBondPremium"] = classifyEBP(ebp_val)
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    # ── Verdad Credit Cycle 4단계 — Greenwood, Hanson, Jin (2019) ──
    result["creditCycle"] = None
    try:
        from dartlab.core.finance.creditCycle import classifyCreditCycle
        from dartlab.macro._helpers import fetch_latest as _fl2
        from dartlab.macro._helpers import get_gather as _gg2

        _g2 = _gg2(as_of)
        _hy2 = _fl2(_g2, "BAMLH0A0HYM2")
        if _hy2 is not None:
            hy_bp2 = _hy2 * 100
            # 6개월 전 HY (방향 판별)
            hy_6m = None
            try:
                from dartlab.macro._helpers import fetch_series_list as _fsl

                hy_list = _fsl(_g2, "BAMLH0A0HYM2")
                if hy_list and len(hy_list) > 125:
                    hy_6m = hy_list[-125] * 100
            except (KeyError, ValueError, TypeError):
                pass

            # Senior Loan Officer Survey (분기, % tightening)
            loan = _fl2(_g2, "DRTSCLCC")
            # Charge-off rate
            co = _fl2(_g2, "CORCCACBS")

            result["creditCycle"] = classifyCreditCycle(
                hy_bp2,
                hy_spread_6m_ago=hy_6m,
                loan_tightening=loan,
                charge_off=co,
            )
    except (KeyError, ValueError, TypeError, AttributeError):
        pass

    from dartlab.macro._helpers import collect_timeseries

    g_ts = get_gather(as_of)
    result["timeseries"] = collect_timeseries(g_ts, {"hy_spread": "BAMLH0A0HYM2", "vix": "VIXCLS", "dxy": "DTWEXBGS"})

    return result


# ── 사이클 위치 기반 행동 추천 ──

_CYCLE_ACTIONS: dict[str, list[dict]] = {
    "recovery": [
        {
            "priority": 1,
            "action": "성장 투자 확대",
            "reason": "경기 회복기 — 수요 증가 시 시장 선점 기회",
            "urgency": "high",
        },
        {
            "priority": 2,
            "action": "레버리지 활용 검토",
            "reason": "저금리 + 경기 호전 → 차입 비용 대비 투자 수익률 우위",
            "urgency": "medium",
        },
    ],
    "expansion": [
        {
            "priority": 1,
            "action": "수익성 극대화",
            "reason": "수요 호조 → 가격 인상 여력, 판관비 효율화 적기",
            "urgency": "medium",
        },
        {
            "priority": 2,
            "action": "현금 축적 시작",
            "reason": "사이클 정점 접근 → 하강기 대비 유보금 확보",
            "urgency": "medium",
        },
    ],
    "late_expansion": [
        {
            "priority": 1,
            "action": "부채 감축 가속화",
            "reason": "금리 상승 + 경기 둔화 시 이자부담 급증",
            "urgency": "high",
        },
        {
            "priority": 2,
            "action": "현금 보유 확대",
            "reason": "경기 하강기 인수 기회 또는 방어 자금",
            "urgency": "high",
        },
        {"priority": 3, "action": "CAPEX 집행 속도 조절", "reason": "투자 수익률 하락 구간 진입", "urgency": "medium"},
    ],
    "slowdown": [
        {
            "priority": 1,
            "action": "비용 구조 긴축",
            "reason": "매출 둔화 시 고정비 부담 급등 → 선제적 구조조정",
            "urgency": "high",
        },
        {
            "priority": 2,
            "action": "운전자본 최적화",
            "reason": "재고 축소, 매출채권 회수 가속화 → 현금 방어",
            "urgency": "high",
        },
    ],
    "contraction": [
        {
            "priority": 1,
            "action": "생존 모드 — 현금 보전",
            "reason": "경기 침체 → 매출 급감, 유동성이 생존 결정",
            "urgency": "critical",
        },
        {
            "priority": 2,
            "action": "저점 인수 기회 탐색",
            "reason": "경쟁사 부실 → 저가 인수 가능, 현금 여력이 전제",
            "urgency": "medium",
        },
    ],
}


def calcCyclicalAction(*, market: str = "KR", as_of: str | None = None, overrides: dict | None = None) -> dict | None:
    """사이클 위치 기반 행동 추천. overrides로 AI 사이클 국면 조율.

    Returns
    -------
    dict | None
        cyclePhase : str
        phaseLabel : str
        actions : list[dict]
        historicalPrecedent : str | None
    """
    # override: cyclePhase 직접 지정
    if overrides and overrides.get("cyclePhase"):
        phase_key = overrides["cyclePhase"]
        actions = _CYCLE_ACTIONS.get(phase_key, _CYCLE_ACTIONS["expansion"])
        return {
            "cyclePhase": phase_key,
            "phaseLabel": f"{phase_key} (AI override)",
            "actions": actions,
            "historicalPrecedent": None,
        }

    try:
        crisis = analyze_crisis(market=market, as_of=as_of)
    except (ValueError, TypeError, KeyError):
        return None

    cycle = crisis.get("cycle", {})
    if not cycle:
        return None

    phase = cycle.get("phase", "")
    label = cycle.get("label", "")

    # phase 매핑
    phase_key = "expansion"
    if "회복" in label or "recovery" in phase.lower():
        phase_key = "recovery"
    elif "확장" in label or "expansion" in phase.lower():
        if "후반" in label or "late" in phase.lower():
            phase_key = "late_expansion"
        else:
            phase_key = "expansion"
    elif "둔화" in label or "slowdown" in phase.lower():
        phase_key = "slowdown"
    elif "침체" in label or "contraction" in phase.lower():
        phase_key = "contraction"

    actions = _CYCLE_ACTIONS.get(phase_key, _CYCLE_ACTIONS["expansion"])

    # 역사적 선례 (historicalContext 활용)
    hc = crisis.get("historicalContext", {})
    events = hc.get("historicalEvents", []) if hc else []
    precedent = None
    if events and isinstance(events[0], dict):
        e = events[0]
        precedent = f"{e.get('eventName', '')} ({e.get('eventDate', '')}) — {e.get('outcome', '')}"

    return {
        "cyclePhase": phase_key,
        "phaseLabel": label or phase_key,
        "actions": actions,
        "historicalPrecedent": precedent,
    }
