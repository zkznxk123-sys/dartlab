"""방법론 적합도 자동 판정 — 이 기업에 이 밸류에이션이 얼마나 맞는가.

DCF는 안정 현금흐름 기업에 맞고, 적��� 기업에는 안 맞는다.
DDM은 연속 배당 기업에만 의미가 있다.
이런 "상식"을 정량화하여 0~1 적합도로 산출.

학술 근거:
- Damodaran: "DCF는 안정 현금흐름 기업에만"
- Penman: "잔여이익은 초과수익률 지속 시"
- Gordon: "배당 지속성이 전제"
"""

from __future__ import annotations

from typing import Any


def calcMethodFitness(company: Any, *, basePeriod: str | None = None) -> dict:
    """각 밸류에이션 방법론의 적합도 자동 판정.

    Returns
    -------
    dict
        dcf : dict — fitness (float 0~1) + reason (str)
        rim : dict
        ddm : dict
        relative : dict
    """
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

        # FCF 양수 비���
        positive_ratio = sum(1 for f in fcfs if f > 0) / len(fcfs)

        # FCF 변동계수 (CV)
        if len(fcfs) >= 3:
            mean = sum(fcfs) / len(fcfs)
            if mean > 0:
                var = sum((f - mean) ** 2 for f in fcfs) / len(fcfs)
                cv = var**0.5 / mean
            else:
                cv = 9.0  # 평균 음수 → ��우 불안정
        else:
            cv = 1.0  # 데이터 부족

        # 적합도 산출
        fitness = 0.5
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

        reason = f"FCF 양수 {positive_ratio:.0%}, 변동계수 {cv:.2f}, {len(fcfs)}년 시계열"
        return {"fitness": round(fitness, 2), "reason": reason}

    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.2, "reason": "현금흐름 분석 실패"}


def _rimFitness(company: Any, basePeriod: str | None) -> dict:
    """RIM 적합도: ROE-CoE Spread + Omega(경쟁우위 지속성)."""
    try:
        from dartlab.analysis.valuation.residualIncome import calcRIM

        rim = calcRIM(company, basePeriod=basePeriod)
        if not rim:
            return {"fitness": 0.2, "reason": "RIM 데이터 부족"}

        omega = getattr(rim, "omega", None) or rim.get("omega") if isinstance(rim, dict) else None
        spread = getattr(rim, "avgSpread", None) or (rim.get("avgSpread") if isinstance(rim, dict) else None)

        fitness = 0.5
        reasons = []

        if omega is not None:
            if omega > 0.6:
                fitness = max(fitness, 0.8)
                reasons.append(f"Omega {omega:.2f} (경쟁우위 지속)")
            elif omega > 0.3:
                fitness = max(fitness, 0.6)
                reasons.append(f"Omega {omega:.2f} (보통)")
            else:
                fitness = min(fitness, 0.3)
                reasons.append(f"Omega {omega:.2f} (우위 약함)")

        if spread is not None:
            if spread > 0:
                fitness = min(fitness + 0.1, 1.0)
                reasons.append(f"Spread +{spread:.1f}%p")
            else:
                fitness = max(fitness - 0.2, 0.1)
                reasons.append(f"Spread {spread:.1f}%p (음수)")

        return {"fitness": round(fitness, 2), "reason": ", ".join(reasons) if reasons else "RIM 기본 ���정"}

    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.3, "reason": "RIM 분석 실패"}


def _ddmFitness(company: Any, basePeriod: str | None) -> dict:
    """DDM 적합도: 연속배당 + 배당성향 안정성."""
    try:
        from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy

        data = calcDividendPolicy(company, basePeriod=basePeriod)
        if not data:
            return {"fitness": 0.0, "reason": "배당 데이터 없음 (무배당 또는 데이터 부족)"}

        consecutive = data.get("consecutiveYears", 0)
        history = data.get("history", [])
        payouts = [h.get("payoutRatio") for h in history if h.get("payoutRatio") is not None]

        if consecutive == 0 or not payouts:
            return {"fitness": 0.0, "reason": "무배당 또는 배당 기록 없음"}

        avg_payout = sum(payouts) / len(payouts)

        fitness = 0.3
        reasons = [f"연속배당 {consecutive}년"]

        if consecutive >= 10:
            fitness = 0.9
        elif consecutive >= 5:
            fitness = 0.7
        elif consecutive >= 3:
            fitness = 0.5

        if avg_payout > 100:
            fitness = max(fitness - 0.3, 0.1)
            reasons.append(f"성향 {avg_payout:.0f}% (이익 ��과 — 지속 불가)")
        elif avg_payout > 80:
            fitness = max(fitness - 0.1, 0.2)
            reasons.append(f"성향 {avg_payout:.0f}% (높음)")
        else:
            reasons.append(f"성향 {avg_payout:.0f}%")

        return {"fitness": round(fitness, 2), "reason": ", ".join(reasons)}

    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.0, "reason": "배당 분석 실패"}


def _relativeFitness(company: Any) -> dict:
    """상대가치 적합도: peer 수 + 업종 분산."""
    try:
        from dartlab.scan.extended import calcPeerPosition

        data = calcPeerPosition(company)
        if not data:
            return {"fitness": 0.3, "reason": "peer 데이터 부족"}

        total = data.get("total_stocks", 0)

        if total >= 50:
            fitness = 0.8
        elif total >= 20:
            fitness = 0.6
        elif total >= 5:
            fitness = 0.4
        else:
            fitness = 0.2

        return {"fitness": round(fitness, 2), "reason": f"peer {total}개사 ��교 가능"}

    except (AttributeError, ValueError, TypeError, KeyError, ImportError):
        return {"fitness": 0.3, "reason": "scan 데이터 접근 불가"}
