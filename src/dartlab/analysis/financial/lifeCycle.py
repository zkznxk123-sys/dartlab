"""Corporate Life Cycle 판별 — Damodaran (2024).

기업의 시간적 위치(생애주기 단계)를 매출 CAGR / 영업마진 추세 / ROIC-WACC spread /
FCF 전환 여부 / 배당성향 조합으로 자동 판별.

storyTemplate (사업 특성) 과 **직교**하는 축 — 삼성전자 는 `사이클 × matureStable`.
밸류에이션 모델 선택은 이 생애주기 단계에 따라 dispatch (dFV.py).

근거: Damodaran, *The Corporate Life Cycle* (Wiley 2024).
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from dartlab.core.overrides import applyOverride

_KR_GROWTH_ADJ = -5.0  # KR 상장사 mid-cycle 정체 → 성장 threshold -5%p

_PHASES = (
    "earlyGrowth",
    "highGrowth",
    "matureGrowth",
    "matureStable",
    "decline",
    "turnaround",
)

_MODEL_HINT = {
    "earlyGrowth": "relativeSurvival",
    "highGrowth": "dcf2stage",
    "matureGrowth": "dcf",
    "matureStable": "dcf",
    "decline": "liquidation",
    "turnaround": "relative",
}


def calcLifeCycle(
    company: Any,
    *,
    basePeriod: str | None = None,
    overrides: dict | None = None,
) -> dict | None:
    """기업 생애주기 단계 판별.

    Returns
    -------
    dict | None
        phase : str — 단계 키 (_PHASES 중 하나)
        phaseConfidence : float — 0.0~1.0
        signals : dict
            revenueCAGR : float — 매출 CAGR (%)
            operatingMarginCV : float — 영업이익률 변동계수
            roicWACCSpread : float — ROIC - WACC 평균 (%p)
            fcfPositiveStreak : int — FCF 양수 연속 기간
            dividendPayout : float — 평균 배당성향 (%)
            marginDirection : str — "expanding" | "stable" | "contracting"
        inflection : dict — {"towards": str | None, "score": float}
        history : list[dict] — 기간별 단계 이력 (최대 5)
        modelHint : str — dFV fitness 가 참조할 밸류에이션 모델 힌트
        source : str — "auto" | "override"
    """
    overrides = overrides or {}

    # override 로 직접 지정된 경우 즉시 반환
    forced = applyOverride(None, "lifeCyclePhase", overrides)
    if forced in _PHASES:
        return {
            "phase": forced,
            "phaseConfidence": 1.0,
            "signals": {},
            "inflection": {"towards": None, "score": 0.0},
            "history": [],
            "modelHint": _MODEL_HINT[forced],
            "source": "override",
        }

    # 신호 수집 — 기존 calc 재사용 (신규 계산 금지)
    signals = _gatherSignals(company, basePeriod=basePeriod)
    if signals is None:
        return None

    # KR 조정
    currency = (getattr(company, "currency", "KRW") or "KRW").upper()
    growth_adj = _KR_GROWTH_ADJ if currency == "KRW" else 0.0

    phase, confidence, history = _classify(signals, growth_adj=growth_adj)
    inflection = _detectInflection(signals, phase)

    return {
        "phase": phase,
        "phaseConfidence": round(confidence, 2),
        "signals": signals,
        "inflection": inflection,
        "history": history,
        "modelHint": _MODEL_HINT.get(phase, "dcf"),
        "source": "auto",
    }


def _gatherSignals(company: Any, *, basePeriod: str | None) -> dict | None:
    """기존 calc 재사용 — lifeCycle 판별 입력 수집."""
    revenue_cagr: float | None = None
    op_margins: list[float] = []
    roic_spreads: list[float] = []
    fcf_streak = 0
    dividend_payout: float | None = None
    margin_direction = "stable"
    revenue_yoys: list[float] = []

    try:
        from dartlab.analysis.financial.growthAnalysis import calcGrowthTrend

        growth = calcGrowthTrend(company, basePeriod=basePeriod)
        if growth:
            revenue_cagr = (growth.get("cagr") or {}).get("revenue")
            for h in growth.get("history", []):
                y = h.get("revenueYoy")
                if isinstance(y, (int, float)):
                    revenue_yoys.append(float(y))
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    try:
        from dartlab.analysis.financial.profitability import calcMarginTrend

        margin = calcMarginTrend(company, basePeriod=basePeriod)
        if margin:
            for h in margin.get("history", []):
                m = h.get("operatingMargin")
                if isinstance(m, (int, float)):
                    op_margins.append(float(m))
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    try:
        from dartlab.analysis.financial.investmentAnalysis import calcRoicTimeline

        roic = calcRoicTimeline(company, basePeriod=basePeriod)
        if roic:
            for h in roic.get("history", []):
                s = h.get("spread")
                if isinstance(s, (int, float)):
                    roic_spreads.append(float(s))
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    try:
        from dartlab.analysis.financial.cashflow import calcCashFlowOverview

        cf = calcCashFlowOverview(company, basePeriod=basePeriod)
        if cf:
            # FCF 양수 연속 기간 (최신부터)
            for h in cf.get("history", []):
                fcf = h.get("fcf")
                if isinstance(fcf, (int, float)) and fcf > 0:
                    fcf_streak += 1
                else:
                    break
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    try:
        from dartlab.analysis.financial.capitalAllocation import calcDividendPolicy

        div = calcDividendPolicy(company, basePeriod=basePeriod)
        if div:
            payouts = [
                h.get("payoutRatio") for h in div.get("history", []) if isinstance(h.get("payoutRatio"), (int, float))
            ]
            if payouts:
                dividend_payout = float(mean(payouts))
    except (ImportError, AttributeError, ValueError, TypeError):
        pass

    # 마진 방향: 최근 3 기간 회귀
    if len(op_margins) >= 3:
        recent = op_margins[:3]
        older = op_margins[-3:]
        if mean(recent) - mean(older) > 2.0:
            margin_direction = "expanding"
        elif mean(recent) - mean(older) < -2.0:
            margin_direction = "contracting"

    # 변동계수 (CV)
    cv = None
    if len(op_margins) >= 3:
        mu = mean(op_margins)
        if mu != 0:
            cv = round(pstdev(op_margins) / abs(mu), 3)

    return {
        "revenueCAGR": revenue_cagr,
        "operatingMarginCV": cv,
        "roicWACCSpread": round(mean(roic_spreads), 2) if roic_spreads else None,
        "fcfPositiveStreak": fcf_streak,
        "dividendPayout": round(dividend_payout, 2) if dividend_payout is not None else None,
        "marginDirection": margin_direction,
        "operatingMarginSeries": op_margins,
        "revenueYoySeries": revenue_yoys,
    }


def _classify(signals: dict, *, growth_adj: float = 0.0) -> tuple[str, float, list[dict]]:
    """신호 → 단계 판별. 보수적 confidence 로 반환."""
    cagr = signals.get("revenueCAGR")
    spread = signals.get("roicWACCSpread")
    fcf_streak = signals.get("fcfPositiveStreak", 0)
    payout = signals.get("dividendPayout") or 0.0
    direction = signals.get("marginDirection")
    margins = signals.get("operatingMarginSeries") or []
    yoys = signals.get("revenueYoySeries") or []

    # 최근 마진 평균 (음수 여부 판단)
    recent_margin = mean(margins[:3]) if len(margins) >= 2 else (margins[0] if margins else None)

    # G20.1: turnaround 우선 강화 — 최근 3년 중 음수 1회 + 최신 양수 (창 확대)
    if len(margins) >= 3:
        recent3 = margins[:3]
        if recent3[0] > 0 and any(m < 0 for m in recent3[1:]) and (cagr is None or cagr > -10):
            return "turnaround", 0.85, _buildHistory(signals)

    # G20.2: decline — 성장 꺾이고 spread 음수 지속
    if isinstance(cagr, (int, float)) and cagr < 0 and (spread is None or spread < -1.0):
        if recent_margin is not None and recent_margin < 5:
            return "decline", 0.75, _buildHistory(signals)
    if len(yoys) >= 3 and all(y < 0 for y in yoys[:3]):
        return "decline", 0.7, _buildHistory(signals)

    # G20.3: matureStable 엄격화 — CAGR<5 AND payout≥40 AND fcf streak≥3 AND spread 작음
    # 모든 조건 충족 시에만 (이전: 일부 충족도 흡수 → matureGrowth/turnaround 사각지대)
    if (
        isinstance(cagr, (int, float))
        and cagr <= 5 + growth_adj
        and payout >= 40
        and fcf_streak >= 3
        and (spread is None or abs(spread) < 3.0)
    ):
        return "matureStable", 0.85, _buildHistory(signals)

    # G20.4: earlyGrowth — 고성장 + 음수 마진 + FCF 음수
    if isinstance(cagr, (int, float)) and cagr >= 30 + growth_adj:
        if recent_margin is not None and recent_margin < 0 and fcf_streak == 0:
            return "earlyGrowth", 0.75, _buildHistory(signals)

    # G20.5: highGrowth — 빠른 성장 + spread 양수 (Damodaran: 고성장기 R&D 확대로 마진 변동 OK)
    if isinstance(cagr, (int, float)) and 15 + growth_adj <= cagr < 35 + growth_adj:
        if spread is None or spread > 0:
            return "highGrowth", 0.75, _buildHistory(signals)

    # G20.6: matureGrowth 활성화 — CAGR 5~18% + spread 양수 (조건 완화: fcf_streak 의무 제거)
    if isinstance(cagr, (int, float)) and 5 + growth_adj <= cagr < 18 + growth_adj:
        if spread is None or spread > 0:
            return "matureGrowth", 0.7, _buildHistory(signals)

    # G20.7: 잔여 — matureStable (보수적 fallback)
    return "matureStable", 0.4, _buildHistory(signals)


def _buildHistory(signals: dict) -> list[dict]:
    """간단한 히스토리 — 판별에 쓴 핵심 신호만 기록."""
    return [
        {
            "signal": "revenueCAGR",
            "value": signals.get("revenueCAGR"),
        },
        {
            "signal": "roicWACCSpread",
            "value": signals.get("roicWACCSpread"),
        },
        {
            "signal": "fcfPositiveStreak",
            "value": signals.get("fcfPositiveStreak"),
        },
        {
            "signal": "dividendPayout",
            "value": signals.get("dividendPayout"),
        },
    ]


def _detectInflection(signals: dict, current_phase: str) -> dict:
    """단계 전환 신호 감지 — 최근 지표 방향성으로."""
    direction = signals.get("marginDirection")
    cagr = signals.get("revenueCAGR")
    margins = signals.get("operatingMarginSeries") or []
    fcf_streak = signals.get("fcfPositiveStreak", 0)

    # matureGrowth → matureStable: 성장 둔화
    if current_phase == "matureGrowth" and isinstance(cagr, (int, float)) and cagr < 8:
        return {"towards": "matureStable", "score": 0.6}
    # matureStable → decline: 마진 하락 + FCF 약화
    if current_phase == "matureStable" and direction == "contracting" and fcf_streak <= 1:
        return {"towards": "decline", "score": 0.55}
    # highGrowth → matureGrowth: CAGR 하락
    if current_phase == "highGrowth" and isinstance(cagr, (int, float)) and cagr < 15:
        return {"towards": "matureGrowth", "score": 0.5}
    # turnaround → highGrowth/matureGrowth: 지속 흑자
    if current_phase == "turnaround" and len(margins) >= 3 and all(m > 0 for m in margins[:3]):
        return {"towards": "matureGrowth", "score": 0.6}
    return {"towards": None, "score": 0.0}
