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
    hySpread: float,
    hySpread6mAgo: float | None = None,
    loanTightening: float | None = None,
    chargeOff: float | None = None,
) -> dict:
    """신용사이클 4단계 판별.

    Capabilities:
        HY 스프레드 수준 + 6개월 방향 + Senior Loan Officer Survey 긴축비중 + Charge-off 추세
        4 지표를 가중 투표 (HY 주도) 로 신용사이클 4 단계 (expansion / peak / contraction / trough)
        판별. Verdad / Howard Marks 식 신용 사이클 위치 진단.

    Args:
        hy_spread: 현재 HY OAS (bp)
        hy_spread_6m_ago: 6개월 전 HY OAS (bp), 방향 판별용
        loan_tightening: Senior Loan Officer Survey (%, 양수=긴축 비중 우세)
        charge_off: Charge-off rate (%, 기업대출 부실률)

    Returns:
        dict with phase, phaseLabel, components, investmentImplication

    Raises:
        없음.

    Example:
        >>> from dartlab.macro.crisis.creditCycleDetect import classifyCreditCycle
        >>> r = classifyCreditCycle(hySpread=350, hySpread6mAgo=420, loanTightening=-5)
        >>> r["phase"]
        'expansion'

    Guide:
        4 단계 시간 순서: expansion → peak → contraction → trough. HY 스프레드 임계
        (very_tight < 350, very_wide > 800) + 방향 (±50bp) 결합.

    When:
        ``macro("crisis", "creditCycle")``. AI 가 채권 / 신용 시장 답변 시.

    How:
        4 지표 각각 임계 매핑 → scores 4 단계 누적 → max → phase 결정.

    Requires:
        - hy_spread 필수. 나머지 옵션 (각각 1 표 추가).

    See Also:
        - ``dartlab.macro.crisis.detectors.creditToGDPGap`` : BIS gap
        - ``dartlab.macro.cycles.cycle.analyzeCycle`` : 매크로 4 국면

    AIContext:
        AI 답변 시 HY 스프레드 + 방향 + phaseLabel 함께 인용. 단일 지표로 단정 금지.
    """
    # ── HY 스프레드 수준 + 방향 ──
    if hySpread < 350:
        hy_level = "very_tight"
    elif hySpread < 450:
        hy_level = "tight"
    elif hySpread < 600:
        hy_level = "normal"
    elif hySpread < 800:
        hy_level = "wide"
    else:
        hy_level = "very_wide"

    hy_direction = "stable"
    if hySpread6mAgo is not None:
        diff = hySpread - hySpread6mAgo
        if diff > 50:
            hy_direction = "widening"
        elif diff < -50:
            hy_direction = "tightening"

    # ── 대출태도 ──
    loan_stance = "unknown"
    if loanTightening is not None:
        if loanTightening > 20:
            loan_stance = "tightening"
        elif loanTightening < -10:
            loan_stance = "easing"
        else:
            loan_stance = "neutral"

    # ── Charge-off 추세 ──
    co_trend = "unknown"
    if chargeOff is not None:
        if chargeOff < 0.3:
            co_trend = "low"
        elif chargeOff < 0.6:
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
        "hySpread": round(hySpread, 1),
        "hyLevel": hy_level,
        "hyDirection": hy_direction,
        "loanStandards": loan_stance,
        "chargeOffTrend": co_trend,
        "scores": {k: v for k, v in scores.items() if v > 0},
        "investmentImplication": _IMPLICATIONS[phase],
        "description": f"신용사이클 {_LABELS[phase]}. HY {hySpread:.0f}bp ({hy_level}), "
        f"대출태도 {loan_stance}, 부실률 {co_trend}.",
    }
