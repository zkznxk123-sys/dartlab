"""질적 조정 — 4엔진 데이터로 적정가 할인/프리미엄 산출.

��치만으로 안 잡히는 기업의 "질" — 신용, 이익품질, 거버넌스, 사이클 —
을 적정가에 반영한다.

학술 근거:
- Sloan (1996): 발생액 이상 → 주가 하방
- Gompers et al. (2003): G-index → 장기 초과수익
- Moody's KMV: PD → credit spread
- Damodaran: Normalized Earnings (사이클 조정)
"""

from __future__ import annotations

from typing import Any


def calcQualityAdjustment(company: Any, *, basePeriod: str | None = None) -> dict:
    """4엔진 데이터로 적정가 질적 조정 계수 산출.

    Returns
    -------
    dict
        totalAdjustment : float — 합산 조정 (-0.18 ~ +0.11)
        factors : list[dict] — 요��별 상세
            name : str
            source : str — 엔진명
            adjustment : float
            reason : str
    """
    factors = []

    # 1. 신용등급 (credit 엔진)
    factors.append(_creditFactor(company, basePeriod))

    # 2. 이익품질 (analysis 엔진)
    factors.append(_earningsQualityFactor(company, basePeriod))

    # 3. 거버넌스 (analysis 엔진)
    factors.append(_governanceFactor(company, basePeriod))

    # 4. 사이클 위치 (macro 엔진)
    factors.append(_cycleFactor(company))

    # 5. 개선 잠재력 (improvement 엔진)
    factors.append(_improvementFactor(company, basePeriod))

    total = sum(f["adjustment"] for f in factors)
    # 클램프: -0.20 ~ +0.11
    total = max(-0.20, min(0.11, total))

    return {"totalAdjustment": round(total, 3), "factors": factors}


def _creditFactor(company: Any, basePeriod: str | None) -> dict:
    """신용등급 → WACC 상당 ���정. dCR AA+ 이상: +3%, BB 이하: -5%."""
    try:
        from dartlab.credit.calcs import calcCreditScore

        data = calcCreditScore(company, basePeriod=basePeriod)
        if not data:
            return {"name": "신용등급", "source": "credit", "adjustment": 0.0, "reason": "등급 데이터 없음"}

        grade = data.get("grade", "")
        score = data.get("score", 50)

        if score <= 20:  # AAA ~ AA+
            return {"name": "신용등급", "source": "credit", "adjustment": 0.03, "reason": f"{grade} — 최고 등급 프리미엄"}
        elif score <= 35:  # AA ~ A
            return {"name": "신용등급", "source": "credit", "adjustment": 0.01, "reason": f"{grade} — 우량"}
        elif score <= 55:  # BBB
            return {"name": "신용등급", "source": "credit", "adjustment": 0.0, "reason": f"{grade} — 투자적격"}
        elif score <= 70:  # BB
            return {"name": "신용등급", "source": "credit", "adjustment": -0.03, "reason": f"{grade} — 투기등급 할인"}
        else:  # B 이하
            return {"name": "신용등급", "source": "credit", "adjustment": -0.05, "reason": f"{grade} — 고위험 할인"}

    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "신용등급", "source": "credit", "adjustment": 0.0, "reason": "신용분석 불가"}


def _earningsQualityFactor(company: Any, basePeriod: str | None) -> dict:
    """이익품질 → 발생액 비율 기반 할인. Sloan (1996)."""
    try:
        from dartlab.analysis.financial.earningsQuality import calcAccrualAnalysis

        data = calcAccrualAnalysis(company, basePeriod=basePeriod)
        if not data:
            return {"name": "이익품질", "source": "analysis", "adjustment": 0.0, "reason": "데이터 ���음"}

        history = data.get("history", [])
        if not history:
            return {"name": "이익품질", "source": "analysis", "adjustment": 0.0, "reason": "���계열 없음"}

        latest = history[-1]
        accrual = latest.get("accrualRatio")
        ocf_ni = latest.get("ocfToNi")

        if accrual is not None and accrual > 25:
            return {"name": "이익품질", "source": "analysis", "adjustment": -0.05, "reason": f"발생액비율 {accrual:.0f}% — 이익 과대 의심"}
        if accrual is not None and accrual > 15:
            return {"name": "이익품질", "source": "analysis", "adjustment": -0.02, "reason": f"발생액비율 {accrual:.0f}% — 보통"}
        if ocf_ni is not None and ocf_ni > 120:
            return {"name": "이익품질", "source": "analysis", "adjustment": 0.02, "reason": f"OCF/NI {ocf_ni:.0f}% — 현금 전환 우수"}

        return {"name": "이익품질", "source": "analysis", "adjustment": 0.0, "reason": "정상 범위"}

    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "이익품질", "source": "analysis", "adjustment": 0.0, "reason": "분석 불가"}


def _governanceFactor(company: Any, basePeriod: str | None) -> dict:
    """거버넌스 → 사외이사 비율 기반. Gompers et al. (2003)."""
    try:
        from dartlab.analysis.financial.governance import calcBoardComposition

        data = calcBoardComposition(company, basePeriod=basePeriod)
        if not data:
            return {"name": "거버넌스", "source": "analysis", "adjustment": 0.0, "reason": "데이터 없음"}

        ratio = data.get("outsideRatio")
        if ratio is None:
            return {"name": "거버넌스", "source": "analysis", "adjustment": 0.0, "reason": "사외이사 데이터 없음"}

        if ratio >= 50:
            return {"name": "거버넌스", "source": "analysis", "adjustment": 0.01, "reason": f"사외이사 {ratio:.0f}% — 독립성 ��호"}
        elif ratio < 25:
            return {"name": "거버넌스", "source": "analysis", "adjustment": -0.03, "reason": f"사외이사 {ratio:.0f}% — 독립성 취약"}

        return {"name": "거버넌스", "source": "analysis", "adjustment": 0.0, "reason": f"사외이사 {ratio:.0f}% — 보통"}

    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "거버넌스", "source": "analysis", "adjustment": 0.0, "reason": "분석 불가"}


def _cycleFactor(company: Any) -> dict:
    """사이클 위치 → earnings power 조정. Damodaran Normalized Earnings."""
    try:
        from dartlab.macro.crisis import calcCyclicalAction

        market = getattr(company, "market", "KR")
        data = calcCyclicalAction(market=market)
        if not data:
            return {"name": "사이클위치", "source": "macro", "adjustment": 0.0, "reason": "사이클 판정 불가"}

        phase = data.get("cyclePhase", "")

        if phase == "contraction":
            return {"name": "사이클위치", "source": "macro", "adjustment": -0.05, "reason": "경기 침체 — earnings power 하향"}
        elif phase == "slowdown":
            return {"name": "사이클위치", "source": "macro", "adjustment": -0.03, "reason": "경기 둔화 — 이익 감소 구간"}
        elif phase == "recovery":
            return {"name": "사이클위치", "source": "macro", "adjustment": 0.03, "reason": "회복 초기 — 이익 반등 기대"}
        elif phase == "late_expansion":
            return {"name": "사이클위치", "source": "macro", "adjustment": -0.02, "reason": "경기 상단부 — 정점 접근"}

        return {"name": "사이클위치", "source": "macro", "adjustment": 0.0, "reason": f"사이클 {phase} — 정상"}

    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "사이클위치", "source": "macro", "adjustment": 0.0, "reason": "매크로 분석 불가"}


def _improvementFactor(company: Any, basePeriod: str | None) -> dict:
    """개선 잠재력 → 상방 프리미엄."""
    try:
        from dartlab.analysis.financial.scenarioSensitivity import calcImprovementLevers

        data = calcImprovementLevers(company, basePeriod=basePeriod)
        if not data or not data.get("levers"):
            return {"name": "개선잠재력", "source": "improvement", "adjustment": 0.0, "reason": "레버 데이터 없음"}

        top = data["levers"][0]
        fcf_change = top.get("impact", {}).get("fcf_change_pct")

        if fcf_change and fcf_change > 20:
            return {"name": "개선잠재력", "source": "improvement", "adjustment": 0.02, "reason": f"톱 레���({top['name']}) FCF +{fcf_change:.0f}% 잠재력"}

        return {"name": "개선잠재력", "source": "improvement", "adjustment": 0.0, "reason": "큰 개선 레버 없음"}

    except (ImportError, AttributeError, ValueError, TypeError):
        return {"name": "개선잠재력", "source": "improvement", "adjustment": 0.0, "reason": "분석 불가"}
