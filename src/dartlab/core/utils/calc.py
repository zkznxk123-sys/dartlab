"""재무 계산 공통 유틸리티 — 단일 정의.

dartlab 전체에서 중복 정의되던 수학 함수를 한 곳으로 통합.
모든 호출자는 여기서 import한다.

규칙:
- division-by-zero → None (0 반환 금지)
- None 인자 → None 반환
- 퍼센트는 *100 후 round(2)
"""

from __future__ import annotations


def safeDiv(a: float | None, b: float | None) -> float | None:
    """안전한 나눗셈. None이나 0 분모 → None."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def safePct(part: float | None, total: float | None) -> float | None:
    """안전한 퍼센트 계산. part/total * 100, round(2)."""
    r = safeDiv(part, total)
    if r is None:
        return None
    return round(r * 100, 2)


def safePctPositive(part: float | None, total: float | None) -> float | None:
    """분모가 양수일 때만 퍼센트. 적자(음수) 분모 → None."""
    if total is not None and total < 0:
        return None
    return safePct(part, total)


def cagr(start: float, end: float, years: int) -> float | None:
    """CAGR (%) 계산. start/end가 음수거나 years ≤ 0이면 None."""
    if start is None or end is None or years is None:
        return None
    if start <= 0 or end <= 0 or years <= 0:
        return None
    try:
        result = ((end / start) ** (1 / years) - 1) * 100
        if isinstance(result, complex):
            return None
        return round(result, 1)
    except (ZeroDivisionError, ValueError, OverflowError, TypeError):
        return None


def decomposeRoic(
    operatingIncome: float | None,
    revenue: float | None,
    investedCapital: float | None,
    effectiveTaxRate: float | None,
    wacc: float | None,
) -> dict | None:
    """ROIC 완전 분해 — Damodaran Investment Valuation Ch.11.

    ROIC = OperatingMargin × AssetTurnover × (1 − EffectiveTaxRate)
    ExcessReturn = (ROIC − WACC) × InvestedCapital

    Returns
    -------
    dict
        operatingMargin : float — OperatingIncome / Revenue (%)
        assetTurnover : float — Revenue / InvestedCapital (회전)
        taxRetention : float — 1 - effectiveTaxRate (0.0~1.0)
        roicReconstructed : float — margin × turnover × taxRetention (%)
        waccPct : float — WACC (%)
        excessReturnPct : float — ROIC - WACC (%p)
        excessReturnAbs : float — (ROIC - WACC) × InvestedCapital (원)
        marginContribution : float — margin × turnover × taxRetention 내 margin 기여분 (%p)
        turnoverContribution : float — 자산회전 기여분 (%p)
        dominantDriver : str — "margin" | "turnover" | "balanced"
    None 이면 입력 부족.
    """
    if operatingIncome is None or revenue is None or investedCapital is None:
        return None
    if revenue <= 0 or investedCapital <= 0:
        return None

    margin = operatingIncome / revenue
    turnover = revenue / investedCapital
    tax = effectiveTaxRate if effectiveTaxRate is not None else 0.22
    tax = max(0.0, min(0.5, tax))
    retention = 1.0 - tax

    roic = margin * turnover * retention
    waccPct = wacc if wacc is not None else 0.0

    # 기여도 분해 — log 공간이 아닌 선형 분해 (Damodaran 권고 단순화)
    # 각 기여분은 "평균값 대비 이 기업의 초과" 가 아니라
    # margin 과 turnover 중 어느 축이 ROIC 를 더 끌어올리는지 상대 비교
    margin_ref = 0.08  # 전산업 평균 영업마진 근사
    turnover_ref = 1.0  # 전산업 평균 자산회전 근사
    margin_contrib = (margin - margin_ref) * turnover * retention
    turnover_contrib = margin_ref * (turnover - turnover_ref) * retention

    if abs(margin_contrib) > abs(turnover_contrib) * 1.5:
        dominant = "margin"
    elif abs(turnover_contrib) > abs(margin_contrib) * 1.5:
        dominant = "turnover"
    else:
        dominant = "balanced"

    invested_abs = investedCapital
    excess_pct = (roic - waccPct / 100.0) * 100.0 if wacc else None
    excess_abs = (roic - waccPct / 100.0) * invested_abs if wacc else None

    return {
        "operatingMargin": round(margin * 100, 2),
        "assetTurnover": round(turnover, 3),
        "taxRetention": round(retention, 3),
        "roicReconstructed": round(roic * 100, 2),
        "waccPct": round(waccPct, 2) if wacc else None,
        "excessReturnPct": round(excess_pct, 2) if excess_pct is not None else None,
        "excessReturnAbs": excess_abs,
        "marginContribution": round(margin_contrib * 100, 2),
        "turnoverContribution": round(turnover_contrib * 100, 2),
        "dominantDriver": dominant,
    }


def reinvestmentIdentity(
    growthRatePct: float | None,
    roicPct: float | None,
) -> dict | None:
    """Damodaran Growth Equation — g = ReinvestmentRate × ROIC.

    Returns
    -------
    dict
        impliedReinvestRate : float — g / ROIC (0.0~1.0)
        growthRatePct : float
        roicPct : float
    """
    if growthRatePct is None or roicPct is None or roicPct == 0:
        return None
    if roicPct <= 0:
        return None
    rate = growthRatePct / roicPct
    return {
        "impliedReinvestRate": round(rate, 4),
        "growthRatePct": round(growthRatePct, 2),
        "roicPct": round(roicPct, 2),
    }
