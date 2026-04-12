"""방법론 적합도 + Primary/Secondary 모델 자동 선택.

기업유형(detectTemplate)에 따라 primary 모델 1개를 선택하고,
나머지는 삼각검증(secondary)으로만 사용한다.

학술 근거:
- McKinsey Valuation Ch.14: "DCF + Triangulation"
- Damodaran: "하나의 서사, 하나의 모델"
- CFA Level II: 기업유형별 모델 선택 매트릭스
"""

from __future__ import annotations

from typing import Any


# ── 기업유형별 모델 선택 매트릭스 ──

_MODEL_MATRIX: dict[str | None, dict] = {
    "프랜차이즈": {"primary": "dcf", "secondary": ["rim", "relative"]},
    "성장": {"primary": "rim", "secondary": ["relative"]},
    "사이클": {"primary": "dcf", "secondary": ["relative"]},  # normalized DCF
    "자본집약": {"primary": "dcf", "secondary": ["relative"]},
    "현금부자": {"primary": "dcf", "secondary": ["rim"]},
    "지주": {"primary": "relative", "secondary": ["rim"]},  # NAV/SOTP 대용
    "턴어라운드": {"primary": "relative", "secondary": []},
    None: {"primary": "dcf", "secondary": ["rim", "relative"]},  # 기본
}


def selectModels(company: Any) -> dict:
    """기업유형 감지 → primary/secondary 모델 자동 선택.

    Returns
    -------
    dict
        companyType : str | None
        primary : str — "dcf" | "rim" | "ddm" | "relative"
        secondary : list[str]
        ddmRole : str — "primary" | "floor" | "excluded"
    """
    template = None
    try:
        from dartlab.review.templates import detectTemplate

        template = detectTemplate(company)
    except (ImportError, AttributeError):
        pass

    matrix = _MODEL_MATRIX.get(template, _MODEL_MATRIX[None])
    primary = matrix["primary"]
    secondary = list(matrix["secondary"])

    # DDM 역할 판정: 고배당 기업에서만 primary
    ddm_role = "floor"  # 기본: 하한선
    try:
        from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy

        div = calcDividendPolicy(company)
        if div:
            payouts = [h.get("payoutRatio") for h in div.get("history", []) if h.get("payoutRatio") is not None]
            consecutive = div.get("consecutiveYears", 0)
            avg_payout = sum(payouts) / len(payouts) if payouts else 0

            if avg_payout >= 60 and consecutive >= 5:
                # 고배당 기업 → DDM primary 승격
                ddm_role = "primary"
                primary = "ddm"
                secondary = ["dcf", "rim"]
            elif consecutive == 0 or avg_payout == 0:
                ddm_role = "excluded"
    except (ImportError, AttributeError, ValueError):
        ddm_role = "excluded"

    return {
        "companyType": template,
        "primary": primary,
        "secondary": secondary,
        "ddmRole": ddm_role,
    }


def calcMethodFitness(company: Any, *, basePeriod: str | None = None) -> dict:
    """각 밸류에이션 방법론의 적합도 자동 판정 (v1 호환 유지)."""
    return {
        "dcf": _dcfFitness(company, basePeriod),
        "rim": _rimFitness(company, basePeriod),
        "ddm": _ddmFitness(company, basePeriod),
        "relative": _relativeFitness(company),
    }


def _dcfFitness(company: Any, basePeriod: str | None) -> dict:
    """DCF 적합도: FCF 안정성 + 시계열 길이."""
    try:
        from dartlab.analysis.financial.cashFlowStructure import calcCashFlowOverview

        data = calcCashFlowOverview(company, basePeriod=basePeriod)
        if not data:
            return {"fitness": 0.2, "reason": "현금흐름 데이터 부족"}

        history = data.get("history", [])
        fcfs = [h.get("fcf") for h in history if h.get("fcf") is not None]
        if not fcfs:
            return {"fitness": 0.1, "reason": "FCF 데이터 없음"}

        positive_ratio = sum(1 for f in fcfs if f > 0) / len(fcfs)

        if len(fcfs) >= 3:
            mean = sum(fcfs) / len(fcfs)
            cv = (sum((f - mean) ** 2 for f in fcfs) / len(fcfs)) ** 0.5 / abs(mean) if mean != 0 else 9.0
        else:
            cv = 1.0

        if positive_ratio >= 0.8 and cv < 0.3:
            fitness = 0.9
        elif positive_ratio >= 0.6 and cv < 0.5:
            fitness = 0.7
        elif positive_ratio >= 0.4:
            fitness = 0.5
        elif positive_ratio > 0:
            fitness = 0.3
        else:
            fitness = 0.1

        return {"fitness": round(fitness, 2), "reason": f"FCF 양수 {positive_ratio:.0%}, CV {cv:.2f}"}
    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.2, "reason": "현금흐름 분석 실패"}


def _rimFitness(company: Any, basePeriod: str | None) -> dict:
    """RIM 적합도: ROE-CoE Spread + Omega."""
    try:
        from dartlab.analysis.valuation.residualIncome import calcRIM

        rim = calcRIM(company, basePeriod=basePeriod)
        if not rim:
            return {"fitness": 0.2, "reason": "RIM 데이터 부족"}

        omega = getattr(rim, "omega", None) or (rim.get("omega") if isinstance(rim, dict) else None)
        fitness = 0.5
        reasons = []

        if omega is not None:
            if omega > 0.6:
                fitness = 0.8
                reasons.append(f"Omega {omega:.2f} (경쟁우위 지속)")
            elif omega > 0.3:
                fitness = 0.6
                reasons.append(f"Omega {omega:.2f}")
            else:
                fitness = 0.3
                reasons.append(f"Omega {omega:.2f} (우위 약함)")

        return {"fitness": round(fitness, 2), "reason": ", ".join(reasons) if reasons else "RIM 기본"}
    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.3, "reason": "RIM 분석 실패"}


def _ddmFitness(company: Any, basePeriod: str | None) -> dict:
    """DDM 적합도: 포괄성(배당성향) × 지속성."""
    try:
        from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy

        data = calcDividendPolicy(company, basePeriod=basePeriod)
        if not data:
            return {"fitness": 0.0, "reason": "무배당"}

        consecutive = data.get("consecutiveYears", 0)
        payouts = [h.get("payoutRatio") for h in data.get("history", []) if h.get("payoutRatio") is not None]
        if not payouts or consecutive == 0:
            return {"fitness": 0.0, "reason": "무배당"}

        avg_payout = sum(payouts) / len(payouts)

        # 포괄성 상한
        if avg_payout < 30:
            cap = 0.25
        elif avg_payout < 50:
            cap = 0.45
        elif avg_payout < 70:
            cap = 0.7
        else:
            cap = 1.0

        base = min(0.3 + consecutive * 0.06, 0.9)  # 연속배당 1년당 +0.06
        fitness = min(base, cap)

        return {"fitness": round(fitness, 2), "reason": f"연속 {consecutive}년, 성향 {avg_payout:.0f}%"}
    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.0, "reason": "배당 분석 실패"}


def _relativeFitness(company: Any) -> dict:
    """상대가치 적합도: peer 수."""
    try:
        from dartlab.scan.extended import calcPeerPosition

        data = calcPeerPosition(company)
        total = data.get("total_stocks", 0) if data else 0
        if total >= 50:
            fitness = 0.8
        elif total >= 20:
            fitness = 0.6
        elif total >= 5:
            fitness = 0.4
        else:
            fitness = 0.2
        return {"fitness": round(fitness, 2), "reason": f"peer {total}개사"}
    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.3, "reason": "scan 데이터 접근 불가"}
