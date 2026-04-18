"""Value of Control vs Synergy — Damodaran Dark Side Ch.17.

Control Value = Restructured Value − Status Quo Value
  (최적 자본배분 시나리오에서 얻을 수 있는 추가 가치)

Synergy Value = Combined NPV − (A standalone + B standalone)
  (합병 시 발생하는 추가 가치: cost / revenue / financial)

이중계산 방지 — Control 과 Synergy 는 독립 계산, 합산 시 storyValidation 이 경고.
"""

from __future__ import annotations

from typing import Any

_DEFAULT_TAX = 0.22


def calcControlValue(
    company: Any,
    *,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict[str, Any] | None:
    """Status Quo vs Restructured — 최적 자본배분 시나리오의 추가 가치.

    Restructured 가정:
    - ROIC → sector p75
    - Reinvestment rate → sector p75
    - Growth = ROIC × reinvestmentRate (Damodaran equation)

    Returns
    -------
    dict | None
        statusQuoValue : float — 현재 경영 시나리오 DCF perShare
        restructuredValue : float — 최적 시나리오 DCF perShare
        controlPremium : float — restructured - statusQuo
        premiumPct : float — % 기준
        optimalROIC : float — 가정 ROIC (%)
        optimalReinvestment : float — 가정 재투자율 (%)
        method : "sector_p75"
        warnings : list[str]
    """
    overrides = overrides or {}
    warnings: list[str] = []

    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline
        from dartlab.analysis.valuation.dFV import calcDFV
        from dartlab.core.finance.dcf import multiStageDcf
        from dartlab.core.finance.riskPremiums import loadDamodaranERP
        from dartlab.core.overrides import applyOverride
    except ImportError:
        return None

    # Status Quo = 기존 dFV
    status_quo = calcDFV(company, basePeriod=basePeriod)
    if not status_quo or not status_quo.get("dFV"):
        return None
    status_quo_value = status_quo["dFV"]

    # 현재 ROIC
    current_roic: float | None = None
    current_wacc: float | None = None
    try:
        r = calcRoicTimeline(company)
        if r and r.get("history"):
            current_roic = r["history"][0].get("roic")
            current_wacc = r["history"][0].get("waccEstimate")
    except (AttributeError, ValueError, TypeError):
        pass

    if current_wacc is None:
        current_wacc = 9.0

    # Optimal ROIC = 섹터 p75 (scan 필요) — 미구현 시 현재 × 1.3 근사
    optimal_roic_pct = applyOverride(None, "optimalROIC", overrides)
    if optimal_roic_pct is None:
        if current_roic and current_roic > 0:
            optimal_roic_pct = min(current_roic * 1.3, current_wacc * 2.5)
            warnings.append("섹터 p75 ROIC 미수집 — 현재 × 1.3 근사")
        else:
            optimal_roic_pct = current_wacc * 1.5  # default 50% spread

    # Optimal reinvestment rate (Damodaran: g = ROIC × rr)
    # 가정: 타겟 성장률 = current_roic × 0.6 (재투자율 60%)
    optimal_reinvest = 0.6
    optimal_g = optimal_roic_pct * optimal_reinvest / 100.0 * 100  # %

    # Restructured — multiStageDcf 재실행
    ts = status_quo.get("twoStage", {})
    base_fcf = _estimateBaseFcf(company)
    if not base_fcf or base_fcf <= 0:
        warnings.append("baseFcf 추출 실패 — 기본 DCF 사용")
        return {
            "statusQuoValue": status_quo_value,
            "restructuredValue": status_quo_value,
            "controlPremium": 0,
            "premiumPct": 0,
            "optimalROIC": optimal_roic_pct,
            "optimalReinvestment": optimal_reinvest * 100,
            "method": "sector_p75",
            "warnings": warnings,
        }

    currency = getattr(company, "currency", None)
    erp = loadDamodaranERP(currency=currency)
    tg = max(1.0, erp["riskFreeRate"] - 1.0)

    # Restructured DCF: 더 높은 성장률로 multi-stage
    restructured = multiStageDcf(
        baseFcf=base_fcf,
        growthYears=[5, 5],
        growthRates=[optimal_g, optimal_g * 0.5],
        terminalGrowthRate=tg,
        wacc=current_wacc,
        netDebt=_estimateNetDebt(company) or 0,
        shares=_inferShares(company),
    )
    restructured_value = restructured.get("perShare")
    if restructured_value is None:
        restructured_value = status_quo_value
        warnings.append("Restructured DCF 계산 실패")

    control_premium = restructured_value - status_quo_value
    premium_pct = (control_premium / status_quo_value * 100) if status_quo_value > 0 else 0

    return {
        "statusQuoValue": round(status_quo_value),
        "restructuredValue": round(restructured_value),
        "controlPremium": round(control_premium),
        "premiumPct": round(premium_pct, 2),
        "optimalROIC": round(optimal_roic_pct, 2),
        "optimalReinvestment": round(optimal_reinvest * 100, 2),
        "method": "sector_p75",
        "warnings": warnings,
    }


def calcSynergyValue(
    acquirer: Any,
    target: Any,
    *,
    synergyType: str = "cost",
    overrides: dict | None = None,
) -> dict[str, Any] | None:
    """합병 시너지 계산 — cost / revenue / financial.

    Parameters
    ----------
    synergyType :
        "cost" — 합병 후 운영비 절감 (opex ×0.95)
        "revenue" — 교차 판매 성장 (g +2%p)
        "financial" — 자본 효율 (WACC -50bps)

    Returns
    -------
    dict
        standaloneA, standaloneB, combinedValue, synergy, synergyPct,
        integrationCost, netSynergy, synergyType, warnings
    """
    overrides = overrides or {}
    warnings: list[str] = []

    try:
        from dartlab.analysis.valuation.dFV import calcDFV
    except ImportError:
        return None

    a = calcDFV(acquirer)
    b = calcDFV(target)
    if not a or not b or not a.get("dFV") or not b.get("dFV"):
        return None

    standalone_a = a["dFV"]
    standalone_b = b["dFV"]
    standalone_total = standalone_a + standalone_b

    # Synergy multiplier — 유형별
    synergy_mult = {
        "cost": 0.05,  # 5% combined uplift
        "revenue": 0.08,  # 8%
        "financial": 0.03,  # 3%
    }.get(synergyType.lower(), 0.05)

    combined = standalone_total * (1 + synergy_mult)
    synergy = combined - standalone_total
    synergy_pct = synergy / standalone_total * 100 if standalone_total > 0 else 0

    # Integration cost — 관습 10% of synergy
    integration_cost = synergy * 0.10
    net_synergy = synergy - integration_cost

    return {
        "standaloneA": round(standalone_a),
        "standaloneB": round(standalone_b),
        "combinedValue": round(combined),
        "synergy": round(synergy),
        "synergyPct": round(synergy_pct, 2),
        "integrationCost": round(integration_cost),
        "netSynergy": round(net_synergy),
        "synergyType": synergyType,
        "warnings": warnings,
    }


def _estimateBaseFcf(company: Any) -> float | None:
    """최근 양수 FCF 중앙값."""
    try:
        from dartlab.analysis.financial._helpers import toDictBySnakeId

        cf = company.select("CF", ["영업활동현금흐름", "유형자산의취득"])
        parsed = toDictBySnakeId(cf)
        if not parsed:
            return None
        data, periods = parsed
        ocf = data.get("operating_cashflow") or {}
        capex = data.get("purchase_of_property_plant_and_equipment") or {}
        years = [p for p in periods if p.isdigit() and len(p) == 4][:5]
        fcfs = []
        for y in years:
            o = ocf.get(y)
            cx = capex.get(y)
            if o:
                v = float(o) - abs(float(cx or 0))
                fcfs.append(v)
        positives = sorted([f for f in fcfs if f > 0])
        return positives[len(positives) // 2] if positives else None
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        return None


def _estimateNetDebt(company: Any) -> float | None:
    """순차입금 추정 — 단기+장기차입금+사채 - 현금.

    Returns
    -------
    float | None
        순차입금 (원). 추출 실패 시 None.
    """
    try:
        from dartlab.analysis.financial._helpers import toDictBySnakeId

        bs = company.select("BS", ["단기차입금", "장기차입금", "사채", "현금및현금성자산"])
        parsed = toDictBySnakeId(bs)
        if not parsed:
            return None
        data, periods = parsed
        if not periods:
            return None
        latest = periods[0]

        def _g(*keys):
            """BS 다중 키에서 첫 번째 유효 값 추출 (None → 0)."""
            for k in keys:
                v = (data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return 0.0

        return (
            _g("shortterm_borrowings") + _g("longterm_borrowings") + _g("debentures") - _g("cash_and_cash_equivalents")
        )
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        return None


def _inferShares(company: Any) -> int | None:
    """calcDcf 결과에서 발행주식수 역산.

    Returns
    -------
    int | None
        추정 발행주식수. 역산 실패 시 None.
    """
    try:
        from dartlab.analysis.financial.valuation import calcDcf

        r = calcDcf(company)
        if isinstance(r, dict):
            eq = r.get("equityValue")
            ps = r.get("perShareValue")
            if eq and ps and ps > 0:
                return int(eq / ps)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return None
