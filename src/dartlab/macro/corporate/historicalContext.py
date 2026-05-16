"""역사적 매크로 팩트 — "과거에 이런 신호가 나왔을 때 무슨 일이 벌어졌나".

L0 순수함수. numpy only, 외부 의존 없음.
FRED 월간 시계열({YYYY-MM: float})과 NBER 침체 날짜로 역사적 통계 계산.

Returns
-------
HistoricalContext
    hySpike : HYSpikeHistory | None — HY 스프레드 급등 → 침체 통계
    yieldCurveInversion : YCInversionHistory | None — 수익률곡선 역전 → 침체 통계
    unemploymentBounce : URBounceHistory | None — 실업률 반등 → 침체 통계
    cpiAcceleration : dict | None — CPI 가속 구간
    simultaneousWarnings : SimultaneousWarnings | None — 동시 경고등 판정
    riskLevel : str — low/moderate/elevated/high
    description : str — 종합 서술
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# 회복기 신호 (bullishSignalFlags + hyCompressionToExpansion) — _historicalContextBullish.py 분리 (BC re-export)
from dartlab.macro.corporate._historicalContextBullish import (  # noqa: F401
    _HISTORICAL_EPOCHS,
    _SIGNATURE_CHECKS,
    bullishSignalFlags,
    hyCompressionToExpansion,
)

# 헬퍼 (분리: _historicalContextHelpers.py SSOT, re-export 으로 BC 보존)
from dartlab.macro.corporate._historicalContextHelpers import (
    _NBER_RECESSIONS,
    _deltaN,
    _isRecession,
    _monthsToNextRecession,
    _yoy,
)

# ── Dataclass ──
# 결과 타입 (분리: _historicalContextTypes.py SSOT, re-export 으로 BC 보존)
from dartlab.macro.corporate._historicalContextTypes import (
    BullishSignals,
    HistoricalContext,
    HistoricalEvent,
    HYCompressionHistory,
    HYSpikeHistory,
    SimultaneousWarnings,
    URBounceHistory,
    YCInversionHistory,
)

# ── 순수함수 ──


def hySpikesToRecession(
    hyMonthly: dict[str, float],
    *,
    thresholdBp: float = 1.0,
    currentDelta: float | None = None,
) -> HYSpikeHistory:
    """HY 스프레드 3개월 급등 → 침체 선행 통계.

    Args:
        hy_monthly: {YYYY-MM: HY spread %}
        threshold_bp: 급등 기준 (%, 기본 1.0 = 100bp)
        current_delta: 현재 3개월 변화 (매칭용)

    Returns:
        HYSpikeHistory
    """
    d3 = _deltaN(hyMonthly, 3)
    spikes: list[tuple[str, float, int, bool]] = []  # (month, delta, months_to_rec, in_rec)

    for m in sorted(d3.keys()):
        if d3[m] > thresholdBp:
            mtr = _monthsToNextRecession(m)
            spikes.append((m, d3[m], mtr, _isRecession(m)))

    # 침체 중이 아닌 급등 → 12개월 내 침체 통계
    pre_rec = [s for s in spikes if not s[3] and s[2] < 999]
    within_12 = sum(1 for s in pre_rec if s[2] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

    # 현재와 가장 유사한 시점
    nearest = None
    nearest_delta = None
    nearest_outcome = None
    if currentDelta is not None and spikes:
        best_diff = float("inf")
        for m, delta, mtr, in_rec in spikes:
            diff = abs(delta - currentDelta)
            if diff < best_diff:
                best_diff = diff
                nearest = m
                nearest_delta = delta
                if in_rec:
                    nearest_outcome = "침체 중"
                elif mtr < 999:
                    nearest_outcome = f"{mtr}개월 후 침체"
                else:
                    nearest_outcome = "침체 없음"

    desc_parts = [f"HY 스프레드 3개월 +{thresholdBp * 100:.0f}bp 이상 급등: 과거 {len(spikes)}회"]
    if pre_rec:
        desc_parts.append(f"12개월 내 침체 {within_12}/{len(pre_rec)} ({rate * 100:.0f}%)")
    if nearest:
        desc_parts.append(f"가장 유사: {nearest} ({nearest_outcome})")

    return HYSpikeHistory(
        totalSpikes=len(spikes),
        recessionWithin12m=within_12,
        recessionRate12m=round(rate, 3),
        nearestMatch=nearest,
        nearestMatchDelta=round(nearest_delta, 2) if nearest_delta else None,
        nearestMatchOutcome=nearest_outcome,
        currentDelta=round(currentDelta, 2) if currentDelta is not None else None,
        description=". ".join(desc_parts),
    )


def yieldCurveInversionsToRecession(
    spreadMonthly: dict[str, float],
) -> YCInversionHistory:
    """Yield Curve 역전 시작점 → 침체까지 통계.

    Args:
        spread_monthly: {YYYY-MM: 10Y-3M spread %}
    """
    months = sorted(spreadMonthly.keys())
    inversions: list[tuple[str, float, int]] = []  # (start_month, spread, months_to_rec)
    prev_positive = True

    for m in months:
        val = spreadMonthly[m]
        if val < 0 and prev_positive:
            mtr = _monthsToNextRecession(m)
            inversions.append((m, val, mtr))
        prev_positive = val >= 0

    valid = [i for i in inversions if i[2] < 999]
    leads = [i[2] for i in valid] if valid else []

    # 현재 역전 상태 확인
    current_start = None
    current_dur = None
    if months:
        latest = months[-1]
        if spreadMonthly[latest] < 0:
            # 역전 시작점 역추적
            for m in reversed(months):
                if spreadMonthly[m] >= 0:
                    break
                current_start = m
            if current_start:
                y1, m1 = int(current_start[:4]), int(current_start[5:7])
                y2, m2 = int(latest[:4]), int(latest[5:7])
                current_dur = (y2 - y1) * 12 + (m2 - m1)

    desc_parts = [f"Yield Curve 역전: 과거 {len(inversions)}회"]
    if leads:
        desc_parts.append(
            f"역전→침체 평균 {np.mean(leads):.0f}개월, 중위 {np.median(leads):.0f}개월 (범위 {min(leads)}~{max(leads)})"
        )
    if current_start:
        desc_parts.append(f"현재 {current_start}부터 역전 중 ({current_dur}개월째)")

    return YCInversionHistory(
        totalInversions=len(inversions),
        avgLeadMonths=round(float(np.mean(leads)), 1) if leads else None,
        medianLeadMonths=round(float(np.median(leads)), 1) if leads else None,
        rangeLeadMonths=(min(leads), max(leads)) if leads else None,
        currentInversionStart=current_start,
        currentDurationMonths=current_dur,
        description=". ".join(desc_parts),
    )


def unemploymentBounceToRecession(
    urMonthly: dict[str, float],
    *,
    thresholdPp: float = 0.3,
) -> URBounceHistory:
    """실업률 12개월 최저에서 반등 → 침체 선행 통계.

    Args:
        ur_monthly: {YYYY-MM: 실업률 %}
        threshold_pp: 반등 기준 (%p)
    """
    months = sorted(urMonthly.keys())
    bounces: list[tuple[str, float, float, int]] = []  # (month, ur, low, mtr)

    for i, m in enumerate(months):
        if i < 12:
            continue
        window = [urMonthly[months[j]] for j in range(i - 12, i + 1)]
        low = min(window)
        bounce = urMonthly[m] - low
        if bounce >= thresholdPp:
            # 이번 달에 처음 돌파?
            prev_bounce = urMonthly[months[i - 1]] - min(urMonthly[months[j]] for j in range(max(0, i - 13), i))
            if prev_bounce < thresholdPp:
                mtr = _monthsToNextRecession(m)
                bounces.append((m, urMonthly[m], low, mtr))

    pre_rec = [b for b in bounces if not _isRecession(b[0]) and b[3] < 999]
    within_12 = sum(1 for b in pre_rec if b[3] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

    # 현재 반등 상태
    current_bounce = None
    if months:
        latest = months[-1]
        i = len(months) - 1
        if i >= 12:
            window = [urMonthly[months[j]] for j in range(i - 12, i + 1)]
            low = min(window)
            current_bounce = round(urMonthly[latest] - low, 2)

    desc_parts = [f"실업률 12개월 저점 대비 +{thresholdPp}%p 이상 반등: 과거 {len(bounces)}회"]
    if pre_rec:
        desc_parts.append(f"12개월 내 침체 {within_12}/{len(pre_rec)} ({rate * 100:.0f}%)")
    if current_bounce is not None and current_bounce >= thresholdPp:
        desc_parts.append(f"현재 저점 대비 +{current_bounce}%p 반등 중")

    return URBounceHistory(
        totalBounces=len(bounces),
        recessionWithin12m=within_12,
        recessionRate12m=round(rate, 3),
        currentBounce=current_bounce,
        description=". ".join(desc_parts),
    )


def cpiAccelerationEvents(
    cpiRawMonthly: dict[str, float],
    *,
    thresholdPp: float = 1.0,
) -> dict:
    """CPI 가속 구간 식별.

    Args:
        cpi_raw_monthly: {YYYY-MM: CPI index}
        threshold_pp: 3개월간 YoY 변화 기준 (%p)

    Returns:
        dict with count, currentAcceleration, description
    """
    cpiYoy = _yoy(cpiRawMonthly)
    accel = _deltaN(cpiYoy, 3)

    events = [(m, accel[m]) for m in sorted(accel.keys()) if accel[m] > thresholdPp]

    # 현재 가속도
    latest_month = max(accel.keys()) if accel else None
    current_accel = accel.get(latest_month) if latest_month else None

    desc = f"CPI 3개월 +{thresholdPp}%p 이상 가속: 과거 {len(events)}회"
    if current_accel is not None and current_accel > thresholdPp:
        desc += f". 현재 +{current_accel:.1f}%p 가속 중"

    return {
        "count": len(events),
        "currentAcceleration": round(current_accel, 2) if current_accel else None,
        "isAccelerating": current_accel is not None and current_accel > thresholdPp,
        "description": desc,
    }


def simultaneousWarningFlags(
    data: dict[str, dict[str, float] | None],
) -> SimultaneousWarnings:
    """8개 경고등 동시 점등 판정.

    Args:
        data: {
            "hy_spread": {YYYY-MM: %},
            "hy_spread_d3": {YYYY-MM: 3m변화},
            "spread_10y2y": {YYYY-MM: %},
            "ur_d6": {YYYY-MM: 6m변화},
            "vix": {YYYY-MM: level},
            "nfci": {YYYY-MM: index},
            "ip_yoy": {YYYY-MM: %},
            "cpi_yoy": {YYYY-MM: %},
        }
    """
    hy = data.get("hy_spread") or {}
    hyD3 = data.get("hy_spread_d3") or {}
    yc = data.get("spread_10y2y") or {}
    urD6 = data.get("ur_d6") or {}
    vixD = data.get("vix") or {}
    nfciD = data.get("nfci") or {}
    ipYoy = data.get("ip_yoy") or {}
    cpiYoy = data.get("cpi_yoy") or {}

    # 공통 월 집합
    all_months = sorted(set(hy.keys()) & set(yc.keys()))

    # 현재 월 경고등
    latest = all_months[-1] if all_months else None
    active: list[str] = []
    if latest:
        if hy.get(latest, 0) > 5:
            active.append("HY>5%")
        if hyD3.get(latest, 0) > 0.5:
            active.append("HY급등")
        if yc.get(latest, 1) < 0:
            active.append("YC역전")
        if urD6.get(latest, 0) > 0.3:
            active.append("실업↑")
        if vixD.get(latest, 0) > 25:
            active.append("VIX>25")
        if nfciD.get(latest, -1) > 0:
            active.append("NFCI긴축")
        if ipYoy.get(latest, 1) < 0:
            active.append("산업생산↓")
        if cpiYoy.get(latest, 0) > 5:
            active.append("CPI>5%")

    # 역사적 동시 점등 통계
    multi_warn_months: list[tuple[str, list[str]]] = []
    for m in all_months:
        flags: list[str] = []
        if hy.get(m, 0) > 5:
            flags.append("HY>5%")
        if hyD3.get(m, 0) > 0.5:
            flags.append("HY급등")
        if yc.get(m, 1) < 0:
            flags.append("YC역전")
        if urD6.get(m, 0) > 0.3:
            flags.append("실업↑")
        if vixD.get(m, 0) > 25:
            flags.append("VIX>25")
        if nfciD.get(m, -1) > 0:
            flags.append("NFCI긴축")
        if ipYoy.get(m, 1) < 0:
            flags.append("산업생산↓")
        if cpiYoy.get(m, 0) > 5:
            flags.append("CPI>5%")
        if len(flags) >= 3:
            multi_warn_months.append((m, flags))

    # 18개월 내 침체 비율
    pre_rec = [(m, flags) for m, flags in multi_warn_months if not _isRecession(m) and _monthsToNextRecession(m) < 999]
    within_18 = sum(1 for m, _ in pre_rec if _monthsToNextRecession(m) <= 18)
    rate = within_18 / len(pre_rec) if pre_rec else 0.0

    # 유사 시기 매칭 (현재 경고등과 겹치는 과거)
    similar: list[dict] = []
    if active:
        active_set = set(active)
        for m, flags in reversed(multi_warn_months):
            if m == latest:
                continue
            overlap = set(flags) & active_set
            if len(overlap) >= 2:
                mtr = _monthsToNextRecession(m)
                outcome = "침체 중" if _isRecession(m) else (f"{mtr}개월 후 침체" if mtr < 24 else "침체 없음")
                similar.append({"month": m, "flags": flags, "outcome": outcome, "overlap": list(overlap)})
            if len(similar) >= 5:
                break

    desc = f"현재 경고등 {len(active)}개"
    if active:
        desc += f" ({', '.join(active)})"
    desc += f". 과거 3개+ 동시 점등 {len(multi_warn_months)}회"
    if pre_rec:
        desc += f", 18개월 내 침체 {within_18}/{len(pre_rec)} ({rate * 100:.0f}%)"

    return SimultaneousWarnings(
        activeFlags=active,
        flagCount=len(active),
        historicalOccurrences=len(multi_warn_months),
        recessionRate18m=round(rate, 3),
        similarPeriods=similar,
        description=desc,
    )


# ══════════════════════════════════════
# 호황/회복 신호 (위기의 반대)
# ══════════════════════════════════════

# NBER 확장 시작점 (침체 종료 다음 달)
_EXPANSION_STARTS: list[str] = [
    "1980-08",
    "1982-12",
    "1991-04",
    "2001-12",
    "2009-07",
    "2020-05",
]


def _extractCurrentSnapshot(data: dict[str, dict[str, float] | None]) -> dict[str, float | None]:
    """10개 거시 시리즈에서 최신 월 값을 뽑아 dict 로 반환."""

    def _latest(d: dict | None) -> float | None:
        if not d:
            return None
        return d[max(d.keys())]

    return {
        "hy": _latest(data.get("hy_spread")),
        "yc": _latest(data.get("spread_10y2y")),
        "ur": _latest(data.get("unrate")),
        "cpi_yoy": _latest(data.get("cpi_yoy")),
        "vix": _latest(data.get("vix")),
        "nfci": _latest(data.get("nfci")),
        "ip_yoy": _latest(data.get("ip_yoy")),
        "ff": _latest(data.get("fedfunds")),
        "hy_d3": _latest(data.get("hy_spread_d3")),
        "ur_d6": _latest(data.get("ur_d6")),
    }


def _scoreSignatureMatch(sig: dict[str, float], curr: dict[str, float | None]) -> tuple[int, int]:
    """signature 대 현재 지표 — (score, checks) 리턴. _SIGNATURE_CHECKS 루프 기반."""
    score = 0
    checks = 0
    for sigKey, currKey, test in _SIGNATURE_CHECKS:
        if sigKey not in sig:
            continue
        currVal = curr.get(currKey)
        if currVal is None:
            continue
        checks += 1
        if test(currVal, sig.get(sigKey)):  # type: ignore[operator]
            score += 1
    return score, checks


def matchHistoricalEvents(
    data: dict[str, dict[str, float] | None],
) -> list[HistoricalEvent]:
    """현재 매크로 상태와 유사한 역사적 사건 매칭 (Q3.1e split).

    _SIGNATURE_CHECKS 테이블 기반 스코어링 → 0.5 이상 매치만 반환 (상위 3).
    """
    curr = _extractCurrentSnapshot(data)
    matches: list[tuple[float, HistoricalEvent]] = []

    for epoch in _HISTORICAL_EPOCHS:
        score, checks = _scoreSignatureMatch(epoch["signature"], curr)
        if checks == 0:
            continue
        match_ratio = score / checks
        if match_ratio < 0.5:
            continue
        similarity = "높음" if match_ratio >= 0.75 else "보통"
        event = HistoricalEvent(
            eventName=epoch["name"],
            eventDate=epoch["period"][0],
            similarity=similarity,
            context=f"조건 {score}/{checks} 매칭 ({match_ratio:.0%})",
            outcome=epoch["outcome"],
        )
        matches.append((match_ratio, event))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:3]]


def _buildSimultaneousWarningData(
    hy, hyD3, spread2y, ur, urD6, vixD, nfciD, ipYoy, cpiYoy
) -> dict[str, dict[str, float] | None]:
    """simultaneousWarningFlags + matchHistoricalEvents 공용 data dict 조립."""
    swData: dict[str, dict[str, float] | None] = {}
    if hy:
        swData["hy_spread"] = hy
        swData["hy_spread_d3"] = hyD3
    if spread2y:
        swData["spread_10y2y"] = spread2y
    if ur:
        swData["ur_d6"] = urD6
    if vixD:
        swData["vix"] = vixD
    if nfciD:
        swData["nfci"] = nfciD
    if ipYoy:
        swData["ip_yoy"] = ipYoy
    if cpiYoy:
        swData["cpi_yoy"] = cpiYoy
    return swData


def _computeRawSignals(hy, hyD3, spread3m, ur, cpiRaw, swData) -> dict:
    """7개 신호 계산: hy/yc/ur/cpi/sw/bull/hy_comp."""
    hy_result = None
    if hy and hyD3:
        latest_hy_month = max(hyD3.keys()) if hyD3 else None
        currentDelta = hyD3.get(latest_hy_month) if latest_hy_month else None
        hy_result = hySpikesToRecession(hy, currentDelta=currentDelta)
    return {
        "hy": hy_result,
        "yc": yieldCurveInversionsToRecession(spread3m) if spread3m else None,
        "ur": unemploymentBounceToRecession(ur) if ur else None,
        "cpi": cpiAccelerationEvents(cpiRaw) if cpiRaw else None,
        "sw": simultaneousWarningFlags(swData) if swData else None,
        "bull": bullishSignalFlags(swData) if swData else None,
        "hy_comp": hyCompressionToExpansion(hy) if hy else None,
    }


def _computeRiskScore(signals: dict) -> int:
    """위기 지표 종합 점수 (0~10+)."""
    hy_result = signals["hy"]
    yc_result = signals["yc"]
    ur_result = signals["ur"]
    cpi_result = signals["cpi"]
    sw_result = signals["sw"]

    risk = 0
    if hy_result and hy_result.currentDelta and hy_result.currentDelta > 1.0:
        risk += 2
    elif hy_result and hy_result.currentDelta and hy_result.currentDelta > 0.5:
        risk += 1
    if yc_result and yc_result.currentInversionStart:
        risk += 2
    if ur_result and ur_result.currentBounce and ur_result.currentBounce >= 0.5:
        risk += 2
    elif ur_result and ur_result.currentBounce and ur_result.currentBounce >= 0.3:
        risk += 1
    if cpi_result and cpi_result.get("isAccelerating"):
        risk += 1
    if sw_result and sw_result.flagCount >= 4:
        risk += 2
    elif sw_result and sw_result.flagCount >= 3:
        risk += 1
    return risk


def _riskLevelFromScore(score: int) -> tuple[str, str]:
    if score >= 6:
        return "high", "위험"
    if score >= 4:
        return "elevated", "주의"
    if score >= 2:
        return "moderate", "관찰"
    return "low", "양호"


def _computeOpportunityScore(signals: dict) -> int:
    """호황 지표 종합 점수."""
    bull_result = signals["bull"]
    hy_comp_result = signals["hy_comp"]
    opp = bull_result.signalCount if bull_result else 0
    if hy_comp_result and hy_comp_result.currentDelta and hy_comp_result.currentDelta < -1.0:
        opp += 2
    return opp


def _opportunityLevelFromScore(score: int) -> tuple[str, str]:
    if score >= 6:
        return "strong", "강한 호황 조짐"
    if score >= 4:
        return "favorable", "우호적"
    if score >= 2:
        return "moderate", "보통"
    return "neutral", "중립"


def _buildDescriptionParts(riskScore: int, label: str, oppLabel: str, signals: dict, events: list) -> list[str]:
    """종합 서술 조립."""
    hy_result = signals["hy"]
    yc_result = signals["yc"]
    sw_result = signals["sw"]
    bull_result = signals["bull"]
    hy_comp_result = signals["hy_comp"]

    parts: list[str] = []
    if riskScore >= 2:
        parts.append(f"위험 수준 {label} ({riskScore}점)")
    if hy_result and hy_result.currentDelta and hy_result.currentDelta > 0.5:
        parts.append(hy_result.description)
    if yc_result and yc_result.currentInversionStart:
        parts.append(yc_result.description)
    if sw_result and sw_result.flagCount >= 2:
        parts.append(sw_result.description)
    if bull_result and bull_result.signalCount >= 3:
        parts.append(bull_result.description)
    if hy_comp_result and hy_comp_result.currentDelta and hy_comp_result.currentDelta < -0.5:
        parts.append(hy_comp_result.description)
    if events:
        top = events[0]
        parts.append(f"역사적 유사 사건: {top.eventName} (유사도 {top.similarity}). 당시 결과: {top.outcome}")
    if not parts:
        parts.append(f"역사적 맥락: 위험 {label}, 기회 {oppLabel}")
    return parts


def _findSuggestedScenario(events: list) -> tuple[str | None, str | None]:
    """최근접 역사 사건 → nextRisk/nextEvent 찾기."""
    if not events:
        return None, None
    top_event = events[0]
    for epoch in _HISTORICAL_EPOCHS:
        if epoch["name"] != top_event.eventName:
            continue
        nr = epoch.get("nextRisk")
        if not nr:
            break
        ne = epoch.get("nextEvent")
        return nr, f"현재 = {top_event.eventName} 유사 ({top_event.similarity}). 당시 다음 장: {ne or nr}"
    return None, None


def buildHistoricalContext(
    data: dict[str, dict[str, float] | None],
) -> HistoricalContext:
    """종합 역사적 맥락 계산 — 위기 + 호황 + 역사적 사건 양방향.

    Args:
        data: {
            "hy_spread": {YYYY-MM: %},
            "spread_10y3m": {YYYY-MM: %},
            "spread_10y2y": {YYYY-MM: %},
            "unrate": {YYYY-MM: %},
            "cpi_raw": {YYYY-MM: index},
            "indpro": {YYYY-MM: index},
            "vix": {YYYY-MM: level},
            "nfci": {YYYY-MM: index},
            "fedfunds": {YYYY-MM: %},  # optional, 역사적 사건 매칭용
        }

    Returns:
        HistoricalContext
    """
    hy = data.get("hy_spread")
    spread3m = data.get("spread_10y3m")
    spread2y = data.get("spread_10y2y")
    ur = data.get("unrate")
    cpiRaw = data.get("cpi_raw")
    indpro = data.get("indpro")
    vixD = data.get("vix")
    nfciD = data.get("nfci")

    hyD3 = _deltaN(hy, 3) if hy else {}
    urD6 = _deltaN(ur, 6) if ur else {}
    ipYoy = _yoy(indpro) if indpro else {}
    cpiYoy = _yoy(cpiRaw) if cpiRaw else {}

    swData = _buildSimultaneousWarningData(hy, hyD3, spread2y, ur, urD6, vixD, nfciD, ipYoy, cpiYoy)

    signals = _computeRawSignals(hy, hyD3, spread3m, ur, cpiRaw, swData)

    event_data = dict(swData)
    if data.get("fedfunds"):
        event_data["fedfunds"] = data["fedfunds"]
    events = matchHistoricalEvents(event_data) if event_data else []

    riskScore = _computeRiskScore(signals)
    level, label = _riskLevelFromScore(riskScore)

    opp_score = _computeOpportunityScore(signals)
    opp_level, oppLabel = _opportunityLevelFromScore(opp_score)

    desc_parts = _buildDescriptionParts(riskScore, label, oppLabel, signals, events)

    suggested_scenario, suggested_reason = _findSuggestedScenario(events)
    if suggested_scenario:
        desc_parts.append(f"다음 장 주의: {suggested_scenario} ({suggested_reason})")

    hy_result = signals["hy"]
    yc_result = signals["yc"]
    ur_result = signals["ur"]
    cpi_result = signals["cpi"]
    sw_result = signals["sw"]
    bull_result = signals["bull"]
    hy_comp_result = signals["hy_comp"]

    return HistoricalContext(
        # 위기
        hySpike=hy_result,
        yieldCurveInversion=yc_result,
        unemploymentBounce=ur_result,
        cpiAcceleration=cpi_result,
        simultaneousWarnings=sw_result,
        # 호황
        bullishSignals=bull_result,
        hyCompression=hy_comp_result,
        # 역사적 사건
        historicalEvents=events or None,
        # 다음 장
        suggestedScenario=suggested_scenario,
        suggestedScenarioReason=suggested_reason,
        # 종합
        riskLevel=level,
        riskLabel=label,
        opportunityLevel=opp_level,
        opportunityLabel=oppLabel,
        description=". ".join(desc_parts),
    )
