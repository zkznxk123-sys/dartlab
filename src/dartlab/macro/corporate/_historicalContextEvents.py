"""역사적 매크로 이벤트 통계 — historicalContext.py 에서 분리.

HY 스프레드 급등, 수익률곡선 역전, 실업률 반등, CPI 가속, 동시 경고등
5 종 이벤트 통계 함수.
"""

from __future__ import annotations

import numpy as np

from dartlab.macro.corporate._historicalContextHelpers import (
    _deltaN,
    _isRecession,
    _monthsToNextRecession,
    _yoy,
)
from dartlab.macro.corporate._historicalContextTypes import (
    HYSpikeHistory,
    SimultaneousWarnings,
    URBounceHistory,
    YCInversionHistory,
)


def hySpikesToRecession(
    hyMonthly: dict[str, float],
    *,
    thresholdBp: float = 1.0,
    currentDelta: float | None = None,
) -> HYSpikeHistory:
    """HY 스프레드 3개월 급등 → 침체 선행 통계."""
    d3 = _deltaN(hyMonthly, 3)
    spikes: list[tuple[str, float, int, bool]] = []

    for m in sorted(d3.keys()):
        if d3[m] > thresholdBp:
            mtr = _monthsToNextRecession(m)
            spikes.append((m, d3[m], mtr, _isRecession(m)))

    pre_rec = [s for s in spikes if not s[3] and s[2] < 999]
    within_12 = sum(1 for s in pre_rec if s[2] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

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
    """Yield Curve 역전 시작점 → 침체까지 통계."""
    months = sorted(spreadMonthly.keys())
    inversions: list[tuple[str, float, int]] = []
    prev_positive = True

    for m in months:
        val = spreadMonthly[m]
        if val < 0 and prev_positive:
            mtr = _monthsToNextRecession(m)
            inversions.append((m, val, mtr))
        prev_positive = val >= 0

    valid = [i for i in inversions if i[2] < 999]
    leads = [i[2] for i in valid] if valid else []

    current_start = None
    current_dur = None
    if months:
        latest = months[-1]
        if spreadMonthly[latest] < 0:
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
    """실업률 12개월 최저에서 반등 → 침체 선행 통계."""
    months = sorted(urMonthly.keys())
    bounces: list[tuple[str, float, float, int]] = []

    for i, m in enumerate(months):
        if i < 12:
            continue
        window = [urMonthly[months[j]] for j in range(i - 12, i + 1)]
        low = min(window)
        bounce = urMonthly[m] - low
        if bounce >= thresholdPp:
            prev_bounce = urMonthly[months[i - 1]] - min(urMonthly[months[j]] for j in range(max(0, i - 13), i))
            if prev_bounce < thresholdPp:
                mtr = _monthsToNextRecession(m)
                bounces.append((m, urMonthly[m], low, mtr))

    pre_rec = [b for b in bounces if not _isRecession(b[0]) and b[3] < 999]
    within_12 = sum(1 for b in pre_rec if b[3] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

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
    """CPI 가속 구간 식별."""
    cpiYoy = _yoy(cpiRawMonthly)
    accel = _deltaN(cpiYoy, 3)

    events = [(m, accel[m]) for m in sorted(accel.keys()) if accel[m] > thresholdPp]

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
    """8개 경고등 동시 점등 판정."""
    hy = data.get("hy_spread") or {}
    hyD3 = data.get("hy_spread_d3") or {}
    yc = data.get("spread_10y2y") or {}
    urD6 = data.get("ur_d6") or {}
    vixD = data.get("vix") or {}
    nfciD = data.get("nfci") or {}
    ipYoy = data.get("ip_yoy") or {}
    cpiYoy = data.get("cpi_yoy") or {}

    all_months = sorted(set(hy.keys()) & set(yc.keys()))

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

    pre_rec = [(m, flags) for m, flags in multi_warn_months if not _isRecession(m) and _monthsToNextRecession(m) < 999]
    within_18 = sum(1 for m, _ in pre_rec if _monthsToNextRecession(m) <= 18)
    rate = within_18 / len(pre_rec) if pre_rec else 0.0

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
