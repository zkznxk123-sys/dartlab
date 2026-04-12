"""하방 시나리오 자동 민감도 — OPM/매출/금리 shock 시 핵심 지표 변화.

"만약 OPM이 5%p 떨어지면?" "매출이 15% 줄면?" "금리가 2%p 오르면?"
각 shock별로 ROE, FCF 커버리지, 이자보상배율 등 핵심 output을 재계산하여
보고서에 리스크/안전마진을 명시한다.

Returns
-------
dict
    baseCase : dict — 현재 핵심 지표
    shocks : dict — 시나리오별 영향
    criticalAssumptions : list[str] — 핵심 가정 목록
    breakdownPoint : dict | None — 손익분기 한계점
"""

from __future__ import annotations

from dartlab.analysis.financial._memoize import memoized_calc


@memoized_calc
def calcScenarioSensitivity(company, *, basePeriod: str | None = None) -> dict | None:
    """핵심 지표 3-shock 민감도 분석.

    Returns
    -------
    dict | None
        baseCase : dict
            opm : float — 영업이익률 (%)
            roe : float — ROE (%)
            interestCoverage : float — 이자보상배율
            debtRatio : float — 부채비율 (%)
            fcf : float — FCF (원)
        shocks : dict
            opm_minus_5pp : dict — OPM -5%p 시
            revenue_minus_15pct : dict — 매출 -15% 시
            interest_plus_2pp : dict — 금리 +2%p 시
        criticalAssumptions : list[str]
        breakdownPoint : dict | None
    """
    from dartlab.analysis.financial._helpers import toDictBySnakeId
    from dartlab.core.finance.helpers import annualColsFromPeriods

    parsed = toDictBySnakeId(
        company.select(
            "IS",
            [
                "sales",
                "operating_income",
                "net_profit",
                "interest_expense",
            ],
        )
    )
    if parsed is None:
        return None
    isData, periods = parsed
    yCols = annualColsFromPeriods(periods, basePeriod=basePeriod, maxYears=1)
    if not yCols:
        return None

    col = yCols[0]

    def _get(row_key: str) -> float | None:
        v = isData.get(row_key, {}).get(col)
        return float(v) if v is not None else None

    revenue = _get("sales")
    op_income = _get("operating_income")
    ni = _get("net_profit")
    interest = _get("interest_expense")

    if revenue is None or op_income is None:
        return None

    opm = op_income / revenue * 100 if revenue else None

    bs_parsed = toDictBySnakeId(company.select("BS", ["total_equity", "total_liabilities"]))
    equity = None
    debt_total = None
    if bs_parsed:
        bsData, bsPeriods = bs_parsed
        bsCols = annualColsFromPeriods(bsPeriods, basePeriod=basePeriod, maxYears=1)
        if bsCols:
            bc = bsCols[0]
            equity = bsData.get("total_equity", {}).get(bc)
            debt_total = bsData.get("total_liabilities", {}).get(bc)
            if equity is not None:
                equity = float(equity)
            if debt_total is not None:
                debt_total = float(debt_total)

    roe = ni / equity * 100 if ni and equity and equity > 0 else None
    debt_ratio = debt_total / equity * 100 if debt_total and equity and equity > 0 else None
    interest_abs = abs(float(interest)) if interest else 0
    ic = op_income / interest_abs if interest_abs > 0 else None

    cf_parsed = toDictBySnakeId(
        company.select("CF", ["operating_cashflow", "purchase_of_property_plant_and_equipment"])
    )
    fcf = None
    if cf_parsed:
        cfData, cfPeriods = cf_parsed
        cfCols = annualColsFromPeriods(cfPeriods, basePeriod=basePeriod, maxYears=1)
        if cfCols:
            cc = cfCols[0]
            ocf = cfData.get("operating_cashflow", {}).get(cc)
            capex = cfData.get("purchase_of_property_plant_and_equipment", {}).get(cc)
            if ocf is not None:
                fcf = float(ocf) - abs(float(capex or 0))

    baseCase = {
        "opm": round(opm, 1) if opm else None,
        "roe": round(roe, 1) if roe else None,
        "interestCoverage": round(ic, 1) if ic else None,
        "debtRatio": round(debt_ratio, 1) if debt_ratio else None,
        "fcf": fcf,
    }

    shocks = {}

    # Shock 1: OPM -5%p
    if opm is not None and revenue:
        shocked_opm = opm - 5
        shocked_op = revenue * shocked_opm / 100
        shocked_ni_est = shocked_op - interest_abs if interest_abs else shocked_op * 0.75
        shocked_roe = shocked_ni_est / equity * 100 if equity and equity > 0 else None
        shocked_ic = shocked_op / interest_abs if interest_abs > 0 else None
        shocks["opm_minus_5pp"] = {
            "opm": round(shocked_opm, 1),
            "roe": round(shocked_roe, 1) if shocked_roe else None,
            "interestCoverage": round(shocked_ic, 1) if shocked_ic else None,
            "verdict": _verdict_opm(shocked_opm, shocked_ic),
        }

    # Shock 2: Revenue -15%
    if revenue and opm is not None:
        shocked_rev = revenue * 0.85
        shocked_op2 = shocked_rev * opm / 100
        shocked_ni2 = shocked_op2 - interest_abs if interest_abs else shocked_op2 * 0.75
        shocked_roe2 = shocked_ni2 / equity * 100 if equity and equity > 0 else None
        shocked_ic2 = shocked_op2 / interest_abs if interest_abs > 0 else None
        shocks["revenue_minus_15pct"] = {
            "revenue_change": "-15%",
            "opm": round(opm, 1),
            "roe": round(shocked_roe2, 1) if shocked_roe2 else None,
            "interestCoverage": round(shocked_ic2, 1) if shocked_ic2 else None,
            "verdict": _verdict_rev(shocked_ic2),
        }

    # Shock 3: Interest +2%p (금리 인상 → 이자비용 증가)
    if interest_abs > 0 and debt_total and debt_total > 0:
        additional_interest = debt_total * 0.02
        shocked_interest = interest_abs + additional_interest
        shocked_ic3 = op_income / shocked_interest if shocked_interest > 0 else None
        shocked_ni3 = op_income - shocked_interest
        shocked_roe3 = shocked_ni3 / equity * 100 if equity and equity > 0 else None
        shocks["interest_plus_2pp"] = {
            "additionalInterest": round(additional_interest),
            "interestCoverage": round(shocked_ic3, 1) if shocked_ic3 else None,
            "roe": round(shocked_roe3, 1) if shocked_roe3 else None,
            "verdict": _verdict_rate(shocked_ic3),
        }

    # 핵심 가정
    assumptions = []
    if opm and opm > 10:
        assumptions.append(f"OPM {opm:.0f}%+ 유지")
    if revenue:
        assumptions.append("매출 성장 > 0")
    if ic and ic > 3:
        assumptions.append("금리 상승 제한적")

    # Breakdown point (OPM)
    breakdown = None
    if revenue and interest_abs > 0:
        bp_opm = interest_abs / revenue * 100
        safety = opm - bp_opm if opm else None
        breakdown = {
            "metric": "opm",
            "value": round(bp_opm, 1),
            "meaning": "이자 비용 감당 한계점",
            "safetyMargin": round(safety, 1) if safety else None,
        }

    return {
        "baseCase": baseCase,
        "shocks": shocks,
        "criticalAssumptions": assumptions,
        "breakdownPoint": breakdown,
    }


def _verdict_opm(opm: float, ic: float | None) -> str:
    if opm < 0:
        return "영업적자 전환"
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    if opm < 5:
        return "마진 압박 심각"
    return "감내 가능"


def _verdict_rev(ic: float | None) -> str:
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    return "감내 가능"


def _verdict_rate(ic: float | None) -> str:
    if ic is not None and ic < 1.5:
        return "이자 감당 위험"
    if ic is not None and ic < 3:
        return "여유 축소"
    return "감내 가능"
