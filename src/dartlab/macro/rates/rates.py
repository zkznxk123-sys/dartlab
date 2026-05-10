"""매크로 금리 분석 — 금리 방향 + 고용/물가 + DKW + Nelson-Siegel."""

from __future__ import annotations

from dartlab.macro.cycles.macroCycle import decomposeLongRate, rateOutlook, realRateRegime
from dartlab.macro.cycles.sentiment import (
    estimateRateExpectation,
    interpretEmployment,
    interpretInflation,
)
from dartlab.macro.rates.yieldCurve import nelsonSiegel
from dartlab.macro.seriesFetch import (
    applyOverrides,
    collectTimeseries,
    fetchLatest,
    fetchYoy,
    getGather,
)


def _fetchPayrolls3mAvg(g) -> float | None:
    """PAYEMS(비농업고용) 최근 3개월 평균 변화.

    PAYEMS는 누적 고용 수준(천명). 월간 변화 = 당월 - 전월.
    최근 3개월 변화의 평균을 반환.

    Parameters
    ----------
    g : Gather
        ``getDefaultGather()`` 로 생성된 Gather 인스턴스.

    Returns
    -------
    float | None
        최근 3개월 비농업고용 월간 변화 평균 (천명). 데이터 부족 시 ``None``.
    """
    try:
        df = g.macro("PAYEMS")
        if df is None or len(df) < 4:
            return None
        vals = df.get_column("value").drop_nulls()
        if len(vals) < 4:
            return None
        recent = [float(v) for v in vals[-4:]]
        changes = [recent[i] - recent[i - 1] for i in range(1, 4)]
        return sum(changes) / 3.0
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


def _fetchRateData(market: str, asOf: str | None = None) -> dict[str, float | None]:
    """gather에서 금리 관련 지표 수집.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.

    Returns
    -------
    dict[str, float]
        None 값은 제거된 채 반환. 가능한 키:

        - fed_funds : float — 연방기금금리 (%)
        - dgs2 : float — 2년 국채금리 (%)
        - dgs10 : float — 10년 국채금리 (%)
        - dfii10 : float — 10년 TIPS 실질금리 (%)
        - t10yie : float — 10년 BEI 기대인플레 (%)
        - t5yie : float — 5년 BEI 기대인플레 (%)
        - unrate : float — 실업률 (%)
        - cpi_yoy : float — CPI 전년비 (%)
        - core_cpi : float — 근원 CPI 전년비 (%)
        - payrolls_3m_avg : float — 비농업고용 3개월 평균 변화 (천명)
        - base_rate : float — 한국 기준금리 (%, KR 전용)
    """
    g = getGather(asOf)
    data: dict[str, float | None] = {}

    if market.upper() == "US":
        for key, sid in [
            ("fed_funds", "FEDFUNDS"),
            ("dgs2", "DGS2"),
            ("dgs10", "DGS10"),
            ("dfii10", "DFII10"),
            ("t10yie", "T10YIE"),
            ("unrate", "UNRATE"),
            ("t5yie", "T5YIE"),
        ]:
            data[key] = fetchLatest(g, sid)

        data["cpi_yoy"] = fetchYoy(g, "CPIAUCSL")
        data["core_cpi"] = fetchYoy(g, "CPILFESL")
        data["payrolls_3m_avg"] = _fetchPayrolls3mAvg(g)

    elif market.upper() == "KR":
        data["base_rate"] = fetchLatest(g, "BASE_RATE")
        data["cpi_yoy"] = fetchYoy(g, "CPI")

    return {k: v for k, v in data.items() if v is not None}


def analyzeRates(*, market: str = "US", asOf: str | None = None, overrides: dict | None = None, **kwargs) -> dict:
    """금리 종합 분석 — 방향 전망 + 고용/물가 해석 + 수익률곡선 분해.

    Parameters
    ----------
    market : str
        ``"US"`` | ``"KR"``.
    as_of : str | None
        기준일. ``None`` 이면 최신.
    overrides : dict | None
        지표 강제 치환 (예: ``{"fed_funds": 5.5}``).

    Returns
    -------
    dict
        - market : str — 시장 코드
        - outlook : dict — 금리 방향 전망 (direction:str, reasoning:list[str])
        - expectation : dict | None — FedWatch 근사 (spread2yFf:float(%p), direction:str, directionLabel:str, strength:str)
        - decomposition : dict | None — DKW 장기금리 분해 (nominal:float(%), expectedInflation:float(%), realRate:float(%), termPremium:float(%p), termPremiumSource:str). US 전용.
        - employment : dict | None — 고용 해석 (state:str, stateLabel:str, reasoning:list[str])
        - inflation : dict | None — 물가 해석 (state:str, stateLabel:str, reasoning:list[str])
        - yieldCurve : dict | None — Nelson-Siegel 분해 (beta0~2:float, lambda:float, rmse:float, interpretation:str, description:str). US 전용.
        - realRateRegime : dict | None — BEI/실질금리 4분면 (realRate:float(%), bei:float(%), regime:str, regimeLabel:str, description:str). US 전용.
        - termPremium : dict | None — ACM 텀프리미엄 (value:float(%p), zone:str, zoneLabel:str, implication:str, description:str). US 전용.
        - bondRiskPremium : dict | None — Cochrane-Piazzesi 채권 리스크 프리미엄. US 전용.
        - timeseries : dict — fed_funds / dgs2 / dgs10 / bei / cpi 시계열
    """
    data = _fetchRateData(market, asOf=asOf)
    if overrides:
        data = applyOverrides(data, overrides)
    result: dict = {"market": market.upper()}

    # 금리 방향 전망
    outlook_input: dict[str, float | None] = {}
    for src, dst in [
        ("fed_funds", "fed_funds"),
        ("base_rate", "base_rate"),
        ("cpi_yoy", "cpi_yoy"),
        ("core_cpi", "core_cpi_yoy"),
        ("unrate", "unemployment"),
    ]:
        if src in data:
            outlook_input[dst] = data[src]
    result["outlook"] = rateOutlook(outlook_input)

    # FedWatch 근사
    ff = data.get("fed_funds") or data.get("base_rate")
    dgs2 = data.get("dgs2")
    dgs10 = data.get("dgs10")
    if ff is not None and dgs2 is not None:
        exp = estimateRateExpectation(ff, dgs2, dgs10)
        result["expectation"] = {
            "spread2yFf": exp.spread2yFf,
            "direction": exp.direction,
            "directionLabel": exp.directionLabel,
            "strength": exp.strength,
        }
    else:
        result["expectation"] = None

    # DKW 분해 (US만)
    result["decomposition"] = None
    if market.upper() == "US" and dgs10 and data.get("t10yie") and data.get("dfii10"):
        acm_tp = fetchLatest(getGather(asOf), "THREEFYTP10")
        decomp = decomposeLongRate(dgs10, data["t10yie"], data["dfii10"], acmTermPremium=acm_tp)
        result["decomposition"] = {
            "nominal": decomp.nominal,
            "expectedInflation": decomp.expectedInflation,
            "realRate": decomp.realRate,
            "termPremium": decomp.termPremium,
            "termPremiumSource": "ACM" if acm_tp is not None else "residual",
        }

    # 고용 해석
    unrate = data.get("unrate")
    if unrate is not None:
        emp = interpretEmployment(unrate, payrolls3mAvg=data.get("payrolls_3m_avg"))
        result["employment"] = {"state": emp.state, "stateLabel": emp.stateLabel, "reasoning": list(emp.reasoning)}
    else:
        result["employment"] = None

    # 물가 해석
    cpi = data.get("cpi_yoy")
    if cpi is not None:
        inf = interpretInflation(cpi, data.get("core_cpi"), data.get("t5yie"), data.get("t10yie"))
        result["inflation"] = {"state": inf.state, "stateLabel": inf.stateLabel, "reasoning": list(inf.reasoning)}
    else:
        result["inflation"] = None

    # Nelson-Siegel 수익률곡선 분해 (US만)
    result["yieldCurve"] = None
    if market.upper() == "US":
        g = getGather(asOf)
        maturities = [1, 2, 3, 5, 7, 10, 20, 30]
        seriesIds = ["DGS1", "DGS2", "DGS3", "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]
        yields_list, valid_mats = [], []
        for mat, sid in zip(maturities, seriesIds):
            val = fetchLatest(g, sid)
            if val is not None:
                yields_list.append(val)
                valid_mats.append(mat)
        if len(valid_mats) >= 4:
            ns = nelsonSiegel(valid_mats, yields_list)
            result["yieldCurve"] = {
                "beta0": ns.beta0,
                "beta1": ns.beta1,
                "beta2": ns.beta2,
                "lambda": ns.lamb,
                "rmse": ns.rmse,
                "interpretation": ns.interpretation,
                "description": ns.description,
            }

    # BEI/실질금리 4분면 (US만)
    result["realRateRegime"] = None
    if market.upper() == "US" and data.get("dfii10") is not None and data.get("t10yie") is not None:
        rr = realRateRegime(data["dfii10"], data["t10yie"])
        result["realRateRegime"] = {
            "realRate": rr.realRate,
            "bei": rr.bei,
            "regime": rr.regime,
            "regimeLabel": rr.regimeLabel,
            "description": rr.description,
        }

    # ── ACM Term Premium — Adrian, Crump, Moench (2013) JFE ──
    # NY Fed 일일 공개 또는 FRED THREEFYTP10
    result["termPremium"] = None
    if market.upper() == "US":
        try:
            tp = fetchLatest(g, "THREEFYTP10")
            if tp is not None:
                if tp < 0:
                    tp_zone, tp_label = "compressed", "압축"
                    tp_impl = "리스크 선호 — 채권 수요 강, 경기 낙관"
                elif tp < 1.0:
                    tp_zone, tp_label = "normal", "정상"
                    tp_impl = "텀프리미엄 정상 범위"
                else:
                    tp_zone, tp_label = "elevated", "상승"
                    tp_impl = "기간 보상 확대 — 경기 불확실성 또는 인플레 우려"
                result["termPremium"] = {
                    "value": round(tp, 3),
                    "zone": tp_zone,
                    "zoneLabel": tp_label,
                    "implication": tp_impl,
                    "description": f"10Y 텀프리미엄 {tp:+.2f}%p ({tp_label}). {tp_impl}.",
                }
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    # ── Cochrane-Piazzesi Factor — CP (2005) AER ──
    # 선도금리 tent-shaped 팩터 → 채권 초과수익 R²=0.44
    result["bondRiskPremium"] = None
    if market.upper() == "US":
        try:
            from dartlab.macro.rates.bondRiskPremia import cochranePiazzesiFactor, forwardRatesFromSpot

            spot = {}
            for mat, sid in [(1, "DGS1"), (2, "DGS2"), (3, "DGS3"), (5, "DGS5")]:
                v = fetchLatest(g, sid)
                if v is not None:
                    spot[mat] = v
            # 4Y는 3Y와 5Y 보간
            if 3 in spot and 5 in spot:
                spot[4] = (spot[3] + spot[5]) / 2
            if len(spot) >= 5:
                forwards = forwardRatesFromSpot(spot)
                cp = cochranePiazzesiFactor(forwards)
                if cp:
                    result["bondRiskPremium"] = cp
        except (KeyError, ValueError, TypeError, AttributeError):
            pass

    # 시계열
    g = getGather(asOf)
    result["timeseries"] = collectTimeseries(
        g,
        {
            "fed_funds": "FEDFUNDS",
            "dgs2": "DGS2",
            "dgs10": "DGS10",
            "bei": "T10YIE",
            "cpi": "CPIAUCSL",
        },
    )

    return result
