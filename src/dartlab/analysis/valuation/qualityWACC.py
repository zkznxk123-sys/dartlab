"""Quality-Adjusted WACC — 4엔진 질적 데이터를 WACC 입력에 내재화.

Fernandez "96 Common Errors": 적정가에 사후 곱셈하지 말고 할인율 입력에서 조정하라.
Moody's KMV: PD → credit spread → WACC.
Gompers et al. (2003): 거버넌스 → equity risk premium.
"""

from __future__ import annotations

from typing import Any


def calcQualityWACC(company: Any, base_wacc: float, *, basePeriod: str | None = None) -> dict:
    """4엔진 질적 요인 → WACC 가감 산출.

    Parameters
    ----------
    company : Company
    base_wacc : float — 기본 WACC (%)

    Returns
    -------
    dict
        adjustedWACC : float — 조정된 WACC (%)
        baseWACC : float
        totalSpread : float — 가감 합계 (%p)
        factors : list[dict]
    """
    factors = []
    factors.append(_creditSpread(company, basePeriod))
    factors.append(_governancePremium(company, basePeriod))
    factors.append(_earningsQualitySpread(company, basePeriod))
    factors.append(_cycleSpread(company))

    total_spread = sum(f["spread"] for f in factors)
    # Phase 4 G12.2: AA 등급 대기업은 시장평균 대비 음수 프리미엄 정당 — 하한 -1.5 → -2.5
    total_spread = max(-2.5, min(5.5, total_spread))
    adjusted = base_wacc + total_spread

    return {
        "adjustedWACC": round(adjusted, 2),
        "baseWACC": base_wacc,
        "totalSpread": round(total_spread, 2),
        "factors": factors,
    }


def _creditSpread(company: Any, basePeriod: str | None) -> dict:
    try:
        data = company.credit("등급") if hasattr(company, "credit") else None
        if not data:
            return {"name": "신용등급", "spread": 0.0, "reason": "등급 없음"}
        score = data.get("score", 50)
        grade = data.get("grade", "")
        if score <= 20:
            return {"name": "신용등급", "spread": -1.0, "reason": f"{grade} — 최우량"}
        elif score <= 35:
            return {"name": "신용등급", "spread": -0.5, "reason": f"{grade} — 우량"}
        elif score <= 55:
            return {"name": "신용등급", "spread": 0.0, "reason": f"{grade} — 투자적격"}
        elif score <= 70:
            return {"name": "신용등급", "spread": 2.0, "reason": f"{grade} — 투기등급"}
        return {"name": "신용등급", "spread": 3.0, "reason": f"{grade} — 고위험"}
    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "신용등급", "spread": 0.0, "reason": "분석 불가"}


def _governancePremium(company: Any, basePeriod: str | None) -> dict:
    try:
        from dartlab.analysis.financial.governance import calcBoardComposition

        data = calcBoardComposition(company, basePeriod=basePeriod)
        if not data:
            return {"name": "거버넌스", "spread": 0.0, "reason": "데이터 없음"}
        ratio = data.get("outsideRatio")
        if ratio is not None and ratio < 25:
            return {"name": "거버넌스", "spread": 1.0, "reason": f"사외이사 {ratio:.0f}%"}
        return {"name": "거버넌스", "spread": 0.0, "reason": f"사외이사 {ratio:.0f}%" if ratio else "없음"}
    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "거버넌스", "spread": 0.0, "reason": "분석 불가"}


def _earningsQualitySpread(company: Any, basePeriod: str | None) -> dict:
    try:
        from dartlab.analysis.financial.earningsQuality import calcAccrualAnalysis

        data = calcAccrualAnalysis(company, basePeriod=basePeriod)
        if not data or not data.get("history"):
            return {"name": "이익품질", "spread": 0.0, "reason": "데이터 없음"}
        accrual = data["history"][-1].get("accrualRatio")
        if accrual is not None and accrual > 25:
            return {"name": "이익품질", "spread": 1.0, "reason": f"발생액 {accrual:.0f}%"}
        return {"name": "이익품질", "spread": 0.0, "reason": "정상"}
    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "이익품질", "spread": 0.0, "reason": "분석 불가"}


def _cycleSpread(company: Any) -> dict:
    try:
        data = company.macro("위기") if hasattr(company, "macro") else None
        if not data:
            return {"name": "사이클", "spread": 0.0, "reason": "판정 불가"}
        phase = data.get("cyclePhase", "")
        spreads = {"contraction": 1.0, "slowdown": 0.5, "late_expansion": 0.5, "recovery": -0.5}
        sp = spreads.get(phase, 0.0)
        return {"name": "사이클", "spread": sp, "reason": f"{data.get('phaseLabel', phase)}"}
    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "사이클", "spread": 0.0, "reason": "분석 불가"}
