"""Verdad-style Credit Cycle 4-phase classifier.

Verdad Capital Research + Greenwood, Hanson, Jin (2019).
신용사이클: 팽창 → 정점 → 수축 → 저점, 3-5년 주기.

지표:
- HY OAS (ICE BofA): 신용 프리미엄 수준 + 방향
- Senior Loan Officer Survey: 은행 대출태도 (긴축/완화)
- Charge-off Rate: 기업 대출 부실률 (후행, 확인 지표)
"""

from __future__ import annotations


def classifyCreditCycle(
    hy_spread: float,
    hy_spread_6m_ago: float | None = None,
    loan_tightening: float | None = None,
    charge_off: float | None = None,
) -> dict:
    """신용사이클 4단계 판별.

    Args:
        hy_spread: 현재 HY OAS (bp)
        hy_spread_6m_ago: 6개월 전 HY OAS (bp), 방향 판별용
        loan_tightening: Senior Loan Officer Survey (%, 양수=긴축 비중 우세)
        charge_off: Charge-off rate (%, 기업대출 부실률)

    Returns:
        dict with phase, phaseLabel, components, investmentImplication
    """
    # ── HY 스프레드 수준 + 방향 ──
    if hy_spread < 350:
        hy_level = "very_tight"
    elif hy_spread < 450:
        hy_level = "tight"
    elif hy_spread < 600:
        hy_level = "normal"
    elif hy_spread < 800:
        hy_level = "wide"
    else:
        hy_level = "very_wide"

    hy_direction = "stable"
    if hy_spread_6m_ago is not None:
        diff = hy_spread - hy_spread_6m_ago
        if diff > 50:
            hy_direction = "widening"
        elif diff < -50:
            hy_direction = "tightening"

    # ── 대출태도 ──
    loan_stance = "unknown"
    if loan_tightening is not None:
        if loan_tightening > 20:
            loan_stance = "tightening"
        elif loan_tightening < -10:
            loan_stance = "easing"
        else:
            loan_stance = "neutral"

    # ── Charge-off 추세 ──
    co_trend = "unknown"
    if charge_off is not None:
        if charge_off < 0.3:
            co_trend = "low"
        elif charge_off < 0.6:
            co_trend = "moderate"
        else:
            co_trend = "elevated"

    # ── 4단계 판별 (다수결 + HY 주도) ──
    scores = {"expansion": 0, "peak": 0, "contraction": 0, "trough": 0}

    # HY 수준 (가장 중요)
    if hy_level in ("very_tight", "tight"):
        scores["expansion"] += 2
        if hy_direction == "tightening":
            scores["expansion"] += 1
        elif hy_direction == "widening":
            scores["peak"] += 2
    elif hy_level == "normal":
        if hy_direction == "widening":
            scores["contraction"] += 2
        else:
            scores["expansion"] += 1
    elif hy_level in ("wide", "very_wide"):
        scores["contraction"] += 2
        if hy_direction == "tightening":
            scores["trough"] += 2
        elif hy_level == "very_wide":
            scores["trough"] += 1

    # 대출태도
    if loan_stance == "easing":
        scores["expansion"] += 1
    elif loan_stance == "tightening":
        scores["contraction"] += 1
    elif loan_stance == "neutral" and hy_level in ("very_tight", "tight"):
        scores["peak"] += 1

    # Charge-off
    if co_trend == "low":
        scores["expansion"] += 1
        scores["peak"] += 1
    elif co_trend == "elevated":
        scores["contraction"] += 1
        scores["trough"] += 1

    # 최고 점수 단계 선택
    phase = max(scores, key=scores.get)  # type: ignore[arg-type]

    _LABELS = {
        "expansion": "팽창",
        "peak": "정점",
        "contraction": "수축",
        "trough": "저점",
    }
    _IMPLICATIONS = {
        "expansion": "신용 확장기 — 레버리지 전략 유효, 크레딧 overweight",
        "peak": "신용 정점 — 스프레드 최저, 리스크 축소 시작 권고",
        "contraction": "신용 수축 — 부실 확대, 크레딧 underweight, 안전자산 선호",
        "trough": "신용 저점 — 역발상 매수 기회, 부실채권/저PBR 매수 고려",
    }

    return {
        "phase": phase,
        "phaseLabel": _LABELS[phase],
        "hySpread": round(hy_spread, 1),
        "hyLevel": hy_level,
        "hyDirection": hy_direction,
        "loanStandards": loan_stance,
        "chargeOffTrend": co_trend,
        "scores": {k: v for k, v in scores.items() if v > 0},
        "investmentImplication": _IMPLICATIONS[phase],
        "description": f"신용사이클 {_LABELS[phase]}. HY {hy_spread:.0f}bp ({hy_level}), "
        f"대출태도 {loan_stance}, 부실률 {co_trend}.",
    }
