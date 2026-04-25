"""인과 추론 (Attribution) — Margin/ROIC/FCF 변화 driver 분해.

McKinsey ROIC Tree + Damodaran *Investment Valuation* Ch.11 표준.

핵심 원칙: 시계열 데이터의 "왜 변했는가" 자동 분해.
영업마진 +3%p 변화 → 원가율/판관비/매출 레버리지/환율 driver 별 기여도.

순수 수학 함수. dict 반환. narrate 는 story 만.
"""

from __future__ import annotations


def decomposeMarginChange(
    revenueT: float,
    revenueT1: float,
    cogsT: float,
    cogsT1: float,
    sgaT: float,
    sgaT1: float,
    *,
    fxImpact: float | None = None,
) -> dict:
    """영업마진 변화의 driver 분해 — Operating Leverage Bridge.

    Operating Margin = (Revenue - COGS - SGA) / Revenue
    ΔMargin = ΔRevenue effect + ΔCOGS effect + ΔSGA effect + FX

    Parameters
    ----------
    revenueT, revenueT1 : 매출 (T 최신, T1 전기)
    cogsT, cogsT1 : 매출원가
    sgaT, sgaT1 : 판매관리비
    fxImpact : 환율 효과 (옵션, %p)

    Returns
    -------
    dict
        marginT, marginT1 : float — %
        marginDelta : float — %p
        drivers : list[{factor, contribution_pp, share_pct}]
        residual : float — 미설명 잔차 (%p)
    """
    if revenueT is None or revenueT1 is None or revenueT <= 0 or revenueT1 <= 0:
        return {"marginDelta": None, "drivers": [], "residual": None}

    cogsT = cogsT or 0
    cogsT1 = cogsT1 or 0
    sgaT = sgaT or 0
    sgaT1 = sgaT1 or 0

    # 마진 계산
    margin_t = (revenueT - cogsT - sgaT) / revenueT * 100
    margin_t1 = (revenueT1 - cogsT1 - sgaT1) / revenueT1 * 100
    delta = margin_t - margin_t1

    # Driver 분해 — 비율 변화 기반
    cogs_ratio_t = cogsT / revenueT * 100
    cogs_ratio_t1 = cogsT1 / revenueT1 * 100
    sga_ratio_t = sgaT / revenueT * 100
    sga_ratio_t1 = sgaT1 / revenueT1 * 100

    # 원가율 개선 기여 (감소면 양수)
    cogs_contrib = -(cogs_ratio_t - cogs_ratio_t1)
    # 판관비 효율 기여
    sga_contrib = -(sga_ratio_t - sga_ratio_t1)

    # 매출 레버리지 — 매출 성장이 고정비 흡수 효과 (단순 근사: 매출 성장률 × 고정비 비중 × 0.3)
    rev_growth = (revenueT / revenueT1 - 1) if revenueT1 > 0 else 0
    fixed_cost_share = sga_ratio_t1 / 100  # SGA 가 주로 고정비
    leverage_contrib = rev_growth * fixed_cost_share * 30  # 경험 계수 0.3 → %p
    # 안전 cap
    leverage_contrib = max(-2.0, min(leverage_contrib, 2.0))

    fx_contrib = float(fxImpact) if fxImpact is not None else 0.0

    drivers_raw = [
        ("원가율 개선", cogs_contrib),
        ("판관비 효율", sga_contrib),
        ("매출 레버리지", leverage_contrib),
    ]
    if fx_contrib != 0:
        drivers_raw.append(("환율 효과", fx_contrib))

    explained = sum(c for _, c in drivers_raw)
    residual = delta - explained

    # share_pct 계산 (절대값 기준)
    abs_total = sum(abs(c) for _, c in drivers_raw)
    drivers = []
    for factor, contrib in drivers_raw:
        share = (abs(contrib) / abs_total * 100) if abs_total > 0 else 0
        drivers.append(
            {
                "factor": factor,
                "contribution_pp": round(contrib, 2),
                "share_pct": round(share, 1),
            }
        )

    return {
        "marginT": round(margin_t, 2),
        "marginT1": round(margin_t1, 2),
        "marginDelta": round(delta, 2),
        "drivers": drivers,
        "residual": round(residual, 2),
        "explainedPct": round(abs(explained) / abs(delta) * 100, 1) if delta != 0 else None,
    }


def decomposeRoicChange(
    roicT: float,
    roicT1: float,
    marginT: float,
    marginT1: float,
    turnoverT: float,
    turnoverT1: float,
    taxT: float,
    taxT1: float,
) -> dict:
    """ROIC 변화 driver 분해 — Damodaran Ch.11.

    ROIC = Margin × Turnover × (1 - Tax)
    ΔROIC = ΔMargin × Turnover_avg + Margin_avg × ΔTurnover + Tax effect

    Parameters
    ----------
    roicT, roicT1 : ROIC (%)
    marginT, marginT1 : 영업마진 (%, NOT decimal)
    turnoverT, turnoverT1 : 자산회전 (회)
    taxT, taxT1 : 유효세율 (%, NOT decimal)

    Returns
    -------
    dict
        roicDelta, drivers, residual
    """
    if any(v is None for v in (roicT, roicT1, marginT, marginT1, turnoverT, turnoverT1)):
        return {"roicDelta": None, "drivers": [], "residual": None}

    delta = roicT - roicT1
    margin_avg = (marginT + marginT1) / 2 / 100  # decimal
    turnover_avg = (turnoverT + turnoverT1) / 2
    tax_avg = (taxT + taxT1) / 2 / 100 if taxT is not None and taxT1 is not None else 0.22
    retention_avg = 1 - tax_avg

    # 마진 변화 기여 (= ΔMargin × Turnover_avg × Retention_avg, %p)
    margin_change = (marginT - marginT1) / 100  # decimal
    margin_contrib = margin_change * turnover_avg * retention_avg * 100  # %p

    # 회전 변화 기여
    turnover_change = turnoverT - turnoverT1
    turnover_contrib = margin_avg * turnover_change * retention_avg * 100

    # 세금 변화 기여 (감세 = 양수)
    tax_change = (taxT - taxT1) / 100 if taxT is not None and taxT1 is not None else 0
    tax_contrib = -margin_avg * turnover_avg * tax_change * 100

    drivers_raw = [
        ("마진 효과", margin_contrib),
        ("자산회전 효과", turnover_contrib),
        ("세금 효과", tax_contrib),
    ]

    explained = sum(c for _, c in drivers_raw)
    residual = delta - explained

    abs_total = sum(abs(c) for _, c in drivers_raw)
    drivers = []
    for factor, contrib in drivers_raw:
        share = (abs(contrib) / abs_total * 100) if abs_total > 0 else 0
        drivers.append(
            {
                "factor": factor,
                "contribution_pp": round(contrib, 2),
                "share_pct": round(share, 1),
            }
        )

    return {
        "roicT": round(roicT, 2),
        "roicT1": round(roicT1, 2),
        "roicDelta": round(delta, 2),
        "drivers": drivers,
        "residual": round(residual, 2),
        "explainedPct": round(abs(explained) / abs(delta) * 100, 1) if delta != 0 else None,
    }


def decomposeFcfChange(
    fcfT: float,
    fcfT1: float,
    ocfT: float,
    ocfT1: float,
    capexT: float,
    capexT1: float,
    *,
    nwcDeltaT: float | None = None,
    nwcDeltaT1: float | None = None,
) -> dict:
    """FCF 변화 bridge — OCF + Capex + NWC.

    FCF = OCF - |Capex|
    ΔFCF = ΔOCF + ΔCapex_savings + ΔNWC

    Parameters
    ----------
    fcfT, fcfT1 : FCF (원)
    ocfT, ocfT1 : 영업CF
    capexT, capexT1 : Capex (음수면 절대값)
    nwcDeltaT, nwcDeltaT1 : 운전자본 변화 (옵션)

    Returns
    -------
    dict
        fcfDelta, drivers, residual
    """
    if any(v is None for v in (fcfT, fcfT1, ocfT, ocfT1)):
        return {"fcfDelta": None, "drivers": [], "residual": None}

    delta = fcfT - fcfT1

    ocf_contrib = ocfT - ocfT1
    capex_contrib = -(abs(capexT or 0) - abs(capexT1 or 0))  # capex 감소 = FCF 증가
    nwc_contrib = 0
    if nwcDeltaT is not None and nwcDeltaT1 is not None:
        nwc_contrib = -(nwcDeltaT - nwcDeltaT1)  # 운전자본 증가 = FCF 감소

    drivers_raw = [
        ("영업CF 변화", ocf_contrib),
        ("CAPEX 변화", capex_contrib),
    ]
    if nwc_contrib != 0:
        drivers_raw.append(("운전자본 변화", nwc_contrib))

    explained = sum(c for _, c in drivers_raw)
    residual = delta - explained

    abs_total = sum(abs(c) for _, c in drivers_raw)
    drivers = []
    for factor, contrib in drivers_raw:
        share = (abs(contrib) / abs_total * 100) if abs_total > 0 else 0
        drivers.append(
            {
                "factor": factor,
                "contribution_amt": float(contrib),
                "share_pct": round(share, 1),
            }
        )

    return {
        "fcfT": float(fcfT),
        "fcfT1": float(fcfT1),
        "fcfDelta": float(delta),
        "drivers": drivers,
        "residual": float(residual),
        "explainedPct": round(abs(explained) / abs(delta) * 100, 1) if delta != 0 else None,
    }
