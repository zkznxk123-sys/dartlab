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

# ── NBER 침체 기간 (미국, 월 단위) ──

_NBER_RECESSIONS: list[tuple[str, str]] = [
    ("1980-01", "1980-07"),
    ("1981-07", "1982-11"),
    ("1990-07", "1991-03"),
    ("2001-03", "2001-11"),
    ("2007-12", "2009-06"),
    ("2020-02", "2020-04"),
]


def _is_recession(month: str) -> bool:
    for start, end in _NBER_RECESSIONS:
        if start <= month <= end:
            return True
    return False


def _months_to_next_recession(month: str) -> int:
    """다음 침체 시작까지 남은 개월 수. 침체 중이면 0. 이후 침체 없으면 999."""
    if _is_recession(month):
        return 0
    for start, _ in _NBER_RECESSIONS:
        if month < start:
            y1, m1 = int(month[:4]), int(month[5:7])
            y2, m2 = int(start[:4]), int(start[5:7])
            return (y2 - y1) * 12 + (m2 - m1)
    return 999


def _delta_n(d: dict[str, float], n: int = 3) -> dict[str, float]:
    """N개월 전 대비 변화량."""
    months = sorted(d.keys())
    idx = {m: i for i, m in enumerate(months)}
    result: dict[str, float] = {}
    for m in months:
        i = idx[m]
        if i >= n:
            result[m] = d[m] - d[months[i - n]]
    return result


def _yoy(d: dict[str, float]) -> dict[str, float]:
    """YoY 변화율 (%)."""
    result: dict[str, float] = {}
    for m, v in d.items():
        y, mo = int(m[:4]), int(m[5:7])
        prev = f"{y - 1:04d}-{mo:02d}"
        if prev in d and abs(d[prev]) > 1e-10:
            result[m] = ((v - d[prev]) / abs(d[prev])) * 100
    return result


# ── Dataclass ──


@dataclass(frozen=True)
class HYSpikeHistory:
    """HY 스프레드 급등 → 침체 통계."""

    totalSpikes: int
    recessionWithin12m: int
    recessionRate12m: float
    nearestMatch: str | None
    nearestMatchDelta: float | None
    nearestMatchOutcome: str | None
    currentDelta: float | None
    description: str


@dataclass(frozen=True)
class YCInversionHistory:
    """Yield Curve 역전 → 침체 통계."""

    totalInversions: int
    avgLeadMonths: float | None
    medianLeadMonths: float | None
    rangeLeadMonths: tuple[int, int] | None
    currentInversionStart: str | None
    currentDurationMonths: int | None
    description: str


@dataclass(frozen=True)
class URBounceHistory:
    """실업률 저점 반등 → 침체 통계."""

    totalBounces: int
    recessionWithin12m: int
    recessionRate12m: float
    currentBounce: float | None
    description: str


@dataclass(frozen=True)
class SimultaneousWarnings:
    """동시 경고등 판정."""

    activeFlags: list[str]
    flagCount: int
    historicalOccurrences: int
    recessionRate18m: float
    similarPeriods: list[dict]
    description: str


@dataclass(frozen=True)
class BullishSignals:
    """호황/회복 신호 — 위기의 반대."""

    activeSignals: list[str]
    signalCount: int
    historicalOccurrences: int
    avgExpansionMonths: float | None
    similarPeriods: list[dict]
    description: str


@dataclass(frozen=True)
class HYCompressionHistory:
    """HY 스프레드 급락 (신용 완화) → 확장 통계."""

    totalCompressions: int
    avgExpansionMonths: float | None
    currentDelta: float | None
    description: str


@dataclass(frozen=True)
class HistoricalEvent:
    """현재와 유사한 역사적 사건."""

    eventName: str
    eventDate: str
    similarity: str  # "높음" | "보통"
    context: str
    outcome: str


@dataclass(frozen=True)
class HistoricalContext:
    """종합 역사적 맥락 — 위기 + 호황 양방향."""

    # 위기 신호
    hySpike: HYSpikeHistory | None = None
    yieldCurveInversion: YCInversionHistory | None = None
    unemploymentBounce: URBounceHistory | None = None
    cpiAcceleration: dict | None = None
    simultaneousWarnings: SimultaneousWarnings | None = None
    # 호황 신호
    bullishSignals: BullishSignals | None = None
    hyCompression: HYCompressionHistory | None = None
    # 역사적 사건 매칭
    historicalEvents: list[HistoricalEvent] | None = None
    # "다음 장" — 역사는 다음 ��이 있다
    suggestedScenario: str | None = None
    suggestedScenarioReason: str | None = None
    # 종합
    riskLevel: str = "low"
    riskLabel: str = "양호"
    opportunityLevel: str = "neutral"
    opportunityLabel: str = "중립"
    description: str = ""


# ── 순수함수 ──


def hySpikesToRecession(
    hy_monthly: dict[str, float],
    *,
    threshold_bp: float = 1.0,
    current_delta: float | None = None,
) -> HYSpikeHistory:
    """HY 스프레드 3개월 급등 → 침체 선행 통계.

    Args:
        hy_monthly: {YYYY-MM: HY spread %}
        threshold_bp: 급등 기준 (%, 기본 1.0 = 100bp)
        current_delta: 현재 3개월 변화 (매칭용)

    Returns:
        HYSpikeHistory
    """
    d3 = _delta_n(hy_monthly, 3)
    spikes: list[tuple[str, float, int, bool]] = []  # (month, delta, months_to_rec, in_rec)

    for m in sorted(d3.keys()):
        if d3[m] > threshold_bp:
            mtr = _months_to_next_recession(m)
            spikes.append((m, d3[m], mtr, _is_recession(m)))

    # 침체 중이 아닌 급등 → 12개월 내 침체 통계
    pre_rec = [s for s in spikes if not s[3] and s[2] < 999]
    within_12 = sum(1 for s in pre_rec if s[2] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

    # 현재와 가장 유사한 시점
    nearest = None
    nearest_delta = None
    nearest_outcome = None
    if current_delta is not None and spikes:
        best_diff = float("inf")
        for m, delta, mtr, in_rec in spikes:
            diff = abs(delta - current_delta)
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

    desc_parts = [f"HY 스프레드 3개월 +{threshold_bp * 100:.0f}bp 이상 급등: 과거 {len(spikes)}회"]
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
        currentDelta=round(current_delta, 2) if current_delta is not None else None,
        description=". ".join(desc_parts),
    )


def yieldCurveInversionsToRecession(
    spread_monthly: dict[str, float],
) -> YCInversionHistory:
    """Yield Curve 역전 시작점 → 침체까지 통계.

    Args:
        spread_monthly: {YYYY-MM: 10Y-3M spread %}
    """
    months = sorted(spread_monthly.keys())
    inversions: list[tuple[str, float, int]] = []  # (start_month, spread, months_to_rec)
    prev_positive = True

    for m in months:
        val = spread_monthly[m]
        if val < 0 and prev_positive:
            mtr = _months_to_next_recession(m)
            inversions.append((m, val, mtr))
        prev_positive = val >= 0

    valid = [i for i in inversions if i[2] < 999]
    leads = [i[2] for i in valid] if valid else []

    # 현재 역전 상태 확인
    current_start = None
    current_dur = None
    if months:
        latest = months[-1]
        if spread_monthly[latest] < 0:
            # 역전 시작점 역추적
            for m in reversed(months):
                if spread_monthly[m] >= 0:
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
    ur_monthly: dict[str, float],
    *,
    threshold_pp: float = 0.3,
) -> URBounceHistory:
    """실업률 12개월 최저에서 반등 → 침체 선행 통계.

    Args:
        ur_monthly: {YYYY-MM: 실업률 %}
        threshold_pp: 반등 기준 (%p)
    """
    months = sorted(ur_monthly.keys())
    bounces: list[tuple[str, float, float, int]] = []  # (month, ur, low, mtr)

    for i, m in enumerate(months):
        if i < 12:
            continue
        window = [ur_monthly[months[j]] for j in range(i - 12, i + 1)]
        low = min(window)
        bounce = ur_monthly[m] - low
        if bounce >= threshold_pp:
            # 이번 달에 처음 돌파?
            prev_bounce = ur_monthly[months[i - 1]] - min(ur_monthly[months[j]] for j in range(max(0, i - 13), i))
            if prev_bounce < threshold_pp:
                mtr = _months_to_next_recession(m)
                bounces.append((m, ur_monthly[m], low, mtr))

    pre_rec = [b for b in bounces if not _is_recession(b[0]) and b[3] < 999]
    within_12 = sum(1 for b in pre_rec if b[3] <= 12)
    rate = within_12 / len(pre_rec) if pre_rec else 0.0

    # 현재 반등 상태
    current_bounce = None
    if months:
        latest = months[-1]
        i = len(months) - 1
        if i >= 12:
            window = [ur_monthly[months[j]] for j in range(i - 12, i + 1)]
            low = min(window)
            current_bounce = round(ur_monthly[latest] - low, 2)

    desc_parts = [f"실업률 12개월 저점 대비 +{threshold_pp}%p 이상 반등: 과거 {len(bounces)}회"]
    if pre_rec:
        desc_parts.append(f"12개월 내 침체 {within_12}/{len(pre_rec)} ({rate * 100:.0f}%)")
    if current_bounce is not None and current_bounce >= threshold_pp:
        desc_parts.append(f"현재 저점 대비 +{current_bounce}%p 반등 중")

    return URBounceHistory(
        totalBounces=len(bounces),
        recessionWithin12m=within_12,
        recessionRate12m=round(rate, 3),
        currentBounce=current_bounce,
        description=". ".join(desc_parts),
    )


def cpiAccelerationEvents(
    cpi_raw_monthly: dict[str, float],
    *,
    threshold_pp: float = 1.0,
) -> dict:
    """CPI 가속 구간 식별.

    Args:
        cpi_raw_monthly: {YYYY-MM: CPI index}
        threshold_pp: 3개월간 YoY 변화 기준 (%p)

    Returns:
        dict with count, currentAcceleration, description
    """
    cpi_yoy = _yoy(cpi_raw_monthly)
    accel = _delta_n(cpi_yoy, 3)

    events = [(m, accel[m]) for m in sorted(accel.keys()) if accel[m] > threshold_pp]

    # 현재 가속도
    latest_month = max(accel.keys()) if accel else None
    current_accel = accel.get(latest_month) if latest_month else None

    desc = f"CPI 3개월 +{threshold_pp}%p 이상 가속: 과거 {len(events)}회"
    if current_accel is not None and current_accel > threshold_pp:
        desc += f". 현재 +{current_accel:.1f}%p 가속 중"

    return {
        "count": len(events),
        "currentAcceleration": round(current_accel, 2) if current_accel else None,
        "isAccelerating": current_accel is not None and current_accel > threshold_pp,
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
    hy_d3 = data.get("hy_spread_d3") or {}
    yc = data.get("spread_10y2y") or {}
    ur_d6 = data.get("ur_d6") or {}
    vix_d = data.get("vix") or {}
    nfci_d = data.get("nfci") or {}
    ip_yoy = data.get("ip_yoy") or {}
    cpi_yoy = data.get("cpi_yoy") or {}

    # 공통 월 집합
    all_months = sorted(set(hy.keys()) & set(yc.keys()))

    # 현재 월 경고등
    latest = all_months[-1] if all_months else None
    active: list[str] = []
    if latest:
        if hy.get(latest, 0) > 5:
            active.append("HY>5%")
        if hy_d3.get(latest, 0) > 0.5:
            active.append("HY급등")
        if yc.get(latest, 1) < 0:
            active.append("YC역전")
        if ur_d6.get(latest, 0) > 0.3:
            active.append("실업↑")
        if vix_d.get(latest, 0) > 25:
            active.append("VIX>25")
        if nfci_d.get(latest, -1) > 0:
            active.append("NFCI긴축")
        if ip_yoy.get(latest, 1) < 0:
            active.append("산업생산↓")
        if cpi_yoy.get(latest, 0) > 5:
            active.append("CPI>5%")

    # 역사적 동시 점등 통계
    multi_warn_months: list[tuple[str, list[str]]] = []
    for m in all_months:
        flags: list[str] = []
        if hy.get(m, 0) > 5:
            flags.append("HY>5%")
        if hy_d3.get(m, 0) > 0.5:
            flags.append("HY급등")
        if yc.get(m, 1) < 0:
            flags.append("YC역전")
        if ur_d6.get(m, 0) > 0.3:
            flags.append("실업↑")
        if vix_d.get(m, 0) > 25:
            flags.append("VIX>25")
        if nfci_d.get(m, -1) > 0:
            flags.append("NFCI긴축")
        if ip_yoy.get(m, 1) < 0:
            flags.append("산업생산↓")
        if cpi_yoy.get(m, 0) > 5:
            flags.append("CPI>5%")
        if len(flags) >= 3:
            multi_warn_months.append((m, flags))

    # 18개월 내 침체 비율
    pre_rec = [
        (m, flags) for m, flags in multi_warn_months if not _is_recession(m) and _months_to_next_recession(m) < 999
    ]
    within_18 = sum(1 for m, _ in pre_rec if _months_to_next_recession(m) <= 18)
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
                mtr = _months_to_next_recession(m)
                outcome = "침체 중" if _is_recession(m) else (f"{mtr}개월 후 침체" if mtr < 24 else "침체 없음")
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


def _months_since_recession_end(month: str) -> int | None:
    """마지막 침체 종료 이후 경과 개월. 침체 중이면 None."""
    if _is_recession(month):
        return None
    for _, end in reversed(_NBER_RECESSIONS):
        if month > end:
            y1, m1 = int(end[:4]), int(end[5:7])
            y2, m2 = int(month[:4]), int(month[5:7])
            return (y2 - y1) * 12 + (m2 - m1)
    return None


def hyCompressionToExpansion(
    hy_monthly: dict[str, float],
    *,
    threshold_bp: float = -1.0,
) -> HYCompressionHistory:
    """HY 스프레드 3개월 급락 (신용 완화) → 확장 통계.

    HY가 빠르게 줄어든다 = 신용 시장이 안정 = 경기 회복/확장 신호.
    """
    d3 = _delta_n(hy_monthly, 3)
    compressions: list[tuple[str, float, int | None]] = []

    for m in sorted(d3.keys()):
        if d3[m] < threshold_bp:
            since = _months_since_recession_end(m)
            compressions.append((m, d3[m], since))

    # 침체 직후 급락인 경우 (회복 초기) — 이후 확장 기간
    recovery_compressions = [c for c in compressions if c[2] is not None and c[2] <= 12]
    expansion_durations = []
    for m, _, _ in recovery_compressions:
        mtr = _months_to_next_recession(m)
        if mtr < 999:
            expansion_durations.append(mtr)

    avg_exp = float(np.mean(expansion_durations)) if expansion_durations else None

    latest = max(d3.keys()) if d3 else None
    current_delta = d3.get(latest) if latest else None

    desc_parts = [
        f"HY 스프레드 3개월 -{abs(threshold_bp) * 100:.0f}bp 이상 급락 (신용 완화): 과거 {len(compressions)}회"
    ]
    if avg_exp:
        desc_parts.append(f"회복 초기 급락 후 평균 {avg_exp:.0f}개월 확장 지속")
    if current_delta is not None and current_delta < threshold_bp:
        desc_parts.append(f"현재 3개월 {current_delta * 100:+.0f}bp — 신용 완화 진행 중")

    return HYCompressionHistory(
        totalCompressions=len(compressions),
        avgExpansionMonths=round(avg_exp, 1) if avg_exp else None,
        currentDelta=round(current_delta, 2) if current_delta is not None else None,
        description=". ".join(desc_parts),
    )


def bullishSignalFlags(
    data: dict[str, dict[str, float] | None],
) -> BullishSignals:
    """호황/회복 신호 감지 — 위기 경고등의 반대.

    8개 긍정 신호:
    - HY<4% (신용 안정)
    - HY 축소 중 (3m<0)
    - YC 양수 (>1.0)
    - 실업률 하락 중 (6m<0)
    - VIX<18 (안정)
    - NFCI<-0.5 (금융환경 완화)
    - 산업생산 성장 (YoY>2%)
    - CPI 안정 (YoY 1~3%)
    """
    hy = data.get("hy_spread") or {}
    hy_d3 = data.get("hy_spread_d3") or {}
    yc = data.get("spread_10y2y") or {}
    ur_d6 = data.get("ur_d6") or {}
    vix_d = data.get("vix") or {}
    nfci_d = data.get("nfci") or {}
    ip_yoy = data.get("ip_yoy") or {}
    cpi_yoy = data.get("cpi_yoy") or {}

    all_months = sorted(set(hy.keys()) & set(yc.keys())) if hy and yc else []
    latest = all_months[-1] if all_months else None

    active: list[str] = []
    if latest:
        if hy.get(latest, 10) < 4:
            active.append("HY<4%")
        if hy_d3.get(latest, 0) < -0.3:
            active.append("HY축소")
        if yc.get(latest, 0) > 1.0:
            active.append("YC양수")
        if ur_d6.get(latest, 0) < 0:
            active.append("실업↓")
        if vix_d.get(latest, 30) < 18:
            active.append("VIX안정")
        if nfci_d.get(latest, 0) < -0.5:
            active.append("NFCI완화")
        if ip_yoy.get(latest, 0) > 2:
            active.append("산업생산↑")
        cpi = cpi_yoy.get(latest, 5)
        if 1 <= cpi <= 3:
            active.append("CPI안정")

    # 역사적 4개+ 동시 점등 통계
    multi_bull: list[tuple[str, list[str]]] = []
    for m in all_months:
        signals: list[str] = []
        if hy.get(m, 10) < 4:
            signals.append("HY<4%")
        if hy_d3.get(m, 0) < -0.3:
            signals.append("HY축소")
        if yc.get(m, 0) > 1.0:
            signals.append("YC양수")
        if ur_d6.get(m, 0) < 0:
            signals.append("실업↓")
        if vix_d.get(m, 30) < 18:
            signals.append("VIX안정")
        if nfci_d.get(m, 0) < -0.5:
            signals.append("NFCI완화")
        if ip_yoy.get(m, 0) > 2:
            signals.append("산업생산↑")
        cpi_v = cpi_yoy.get(m, 5)
        if 1 <= cpi_v <= 3:
            signals.append("CPI안정")
        if len(signals) >= 4:
            multi_bull.append((m, signals))

    # 4개+ 호황 신호 후 확장 지속 기간
    expansion_months = []
    for m, _ in multi_bull:
        mtr = _months_to_next_recession(m)
        if mtr < 999 and not _is_recession(m):
            expansion_months.append(mtr)
    avg_exp = float(np.mean(expansion_months)) if expansion_months else None

    # 유사 시기
    similar: list[dict] = []
    if active:
        active_set = set(active)
        for m, signals in reversed(multi_bull):
            if m == latest:
                continue
            overlap = set(signals) & active_set
            if len(overlap) >= 3:
                mtr = _months_to_next_recession(m)
                outcome = f"{mtr}개월 확장 지속" if mtr < 999 and not _is_recession(m) else "확장 중"
                similar.append({"month": m, "signals": signals, "outcome": outcome, "overlap": list(overlap)})
            if len(similar) >= 5:
                break

    desc = f"호황 신호 {len(active)}개"
    if active:
        desc += f" ({', '.join(active)})"
    desc += f". 과거 4개+ 동시 {len(multi_bull)}회"
    if avg_exp:
        desc += f", 이후 평균 {avg_exp:.0f}개월 확장"

    return BullishSignals(
        activeSignals=active,
        signalCount=len(active),
        historicalOccurrences=len(multi_bull),
        avgExpansionMonths=round(avg_exp, 1) if avg_exp else None,
        similarPeriods=similar,
        description=desc,
    )


# ══════════════════════════════════════
# 역사적 사건 매칭
# ══════════════════════════════════════

_HISTORICAL_EPOCHS: list[dict] = [
    {
        "name": "볼커 긴축 (1980-81)",
        "period": ("1980-01", "1982-11"),
        "signature": {"cpi_yoy_high": 8, "ff_high": 10, "ur_high": 7},
        "outcome": "인플레 진압 → 1983~89 장기 확장",
        "nextRisk": "골디락스",
        "nextEvent": "1983~89 장기 확장",
    },
    {
        "name": "골디락스 (1995-98)",
        "period": ("1995-01", "1998-06"),
        "signature": {"cpi_yoy_low": 3, "ur_low": 5.5, "vix_low": 20, "yc_positive": True},
        "outcome": "저인플레 + 완전고용 + 주식 강세 42개월",
        "nextRisk": "자산 버블 붕괴",
        "nextEvent": "IT 버블 정점 (2000) → NASDAQ -78%",
    },
    {
        "name": "IT 버블 정점 (2000)",
        "period": ("1999-06", "2000-09"),
        "signature": {"vix_low": 25, "yc_inverted": True, "ip_strong": True},
        "outcome": "NASDAQ -78%, 2001-03 침체 시작",
        "nextRisk": "신용 충격",
        "nextEvent": "2001 침체 → 2001-03~2001-11",
    },
    {
        "name": "금융위기 (2008)",
        "period": ("2007-12", "2009-03"),
        "signature": {"hy_high": 8, "nfci_tight": True, "ur_rising": True, "ip_falling": True},
        "outcome": "S&P -57%, 실업률 10%, 2009-03 저점 후 V자 반등",
        "nextRisk": "연착륙",
        "nextEvent": "2009 대반등 → 112개월 확장",
    },
    {
        "name": "2009 대반등",
        "period": ("2009-03", "2010-06"),
        "signature": {"hy_falling": True, "nfci_easing": True, "vix_falling": True},
        "outcome": "S&P +80% (12개월), 112개월 확장 시작",
        "nextRisk": "신용 충격",
        "nextEvent": "유럽 재정위기 (2011) → S&P -19%",
    },
    {
        "name": "유럽 재정위기 (2011)",
        "period": ("2011-07", "2011-12"),
        "signature": {"hy_high": 6, "vix_high": 30, "yc_positive": True},
        "outcome": "V자 반등, 위기는 유럽에 국한",
        "nextRisk": "골디락스",
        "nextEvent": "2012~2018 장기 확장",
    },
    {
        "name": "연준 긴축 쇼크 (2018말)",
        "period": ("2018-10", "2019-01"),
        "signature": {"hy_rising": True, "vix_high": 25, "yc_flat": True, "ff_rising": True},
        "outcome": "연준 피벗(금리 동결) → 2019 강세장",
        "nextRisk": "지정학/팬데믹",
        "nextEvent": "COVID 충격 (2020-03)",
    },
    {
        "name": "COVID 충격 (2020-03)",
        "period": ("2020-02", "2020-04"),
        "signature": {"vix_high": 40, "hy_high": 8, "nfci_tight": True, "ip_falling": True},
        "outcome": "역사상 최단 침체(2개월), V자 반등, 양적완화",
        "nextRisk": "인플레이션 충격",
        "nextEvent": "인플레 긴축 (2022) → CPI 9.1%",
    },
    {
        "name": "인플레 긴축 (2022)",
        "period": ("2022-01", "2022-12"),
        "signature": {"cpi_yoy_high": 5, "ff_rising": True, "yc_inverted": True},
        "outcome": "NASDAQ -33%, 하지만 침체 회피",
        "nextRisk": "골디락스",
        "nextEvent": "AI 강세장 (2023-24) → 연착륙",
    },
    {
        "name": "AI 강세장 (2023-24)",
        "period": ("2023-01", "2024-12"),
        "signature": {"vix_low": 20, "ur_low": 4.5, "ip_stable": True, "hy_low": 4},
        "outcome": "NASDAQ +85%, 연착륙 기대",
        "nextRisk": "AI 버블 붕괴",
        "nextEvent": "??? (진행 중)",
    },
]


# signature 조건 → (curr 키, 비교 함수 (값, 임계값) → bool)
# 임계값 없는 키는 sig 내 boolean flag 만 검사 (두 번째 인자 무시).
_SIGNATURE_CHECKS: list[tuple[str, str, object]] = [
    ("cpi_yoy_high", "cpi_yoy", lambda v, t: v >= t),
    ("cpi_yoy_low", "cpi_yoy", lambda v, t: v <= t),
    ("ff_high", "ff", lambda v, t: v >= t),
    ("ff_rising", "ff", lambda v, _t: v > 3),
    ("ur_high", "ur", lambda v, t: v >= t),
    ("ur_low", "ur", lambda v, t: v <= t),
    ("ur_rising", "ur_d6", lambda v, _t: v > 0.3),
    ("vix_high", "vix", lambda v, t: v >= t),
    ("vix_low", "vix", lambda v, t: v <= t),
    ("vix_falling", "vix", lambda v, _t: v < 20),
    ("hy_high", "hy", lambda v, t: v >= t),
    ("hy_low", "hy", lambda v, t: v <= t),
    ("hy_rising", "hy_d3", lambda v, _t: v > 0.5),
    ("hy_falling", "hy_d3", lambda v, _t: v < -0.5),
    ("yc_inverted", "yc", lambda v, _t: v < 0),
    ("yc_positive", "yc", lambda v, _t: v > 0.5),
    ("yc_flat", "yc", lambda v, _t: -0.3 <= v <= 0.3),
    ("nfci_tight", "nfci", lambda v, _t: v > 0),
    ("nfci_easing", "nfci", lambda v, _t: v < -0.3),
    ("ip_falling", "ip_yoy", lambda v, _t: v < 0),
    ("ip_strong", "ip_yoy", lambda v, _t: v > 3),
    ("ip_stable", "ip_yoy", lambda v, _t: v > -1),
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
    hy, hy_d3, spread_2y, ur, ur_d6, vix_d, nfci_d, ip_yoy, cpi_yoy
) -> dict[str, dict[str, float] | None]:
    """simultaneousWarningFlags + matchHistoricalEvents 공용 data dict 조립."""
    sw_data: dict[str, dict[str, float] | None] = {}
    if hy:
        sw_data["hy_spread"] = hy
        sw_data["hy_spread_d3"] = hy_d3
    if spread_2y:
        sw_data["spread_10y2y"] = spread_2y
    if ur:
        sw_data["ur_d6"] = ur_d6
    if vix_d:
        sw_data["vix"] = vix_d
    if nfci_d:
        sw_data["nfci"] = nfci_d
    if ip_yoy:
        sw_data["ip_yoy"] = ip_yoy
    if cpi_yoy:
        sw_data["cpi_yoy"] = cpi_yoy
    return sw_data


def _computeRawSignals(hy, hy_d3, spread_3m, ur, cpi_raw, sw_data) -> dict:
    """7개 신호 계산: hy/yc/ur/cpi/sw/bull/hy_comp."""
    hy_result = None
    if hy and hy_d3:
        latest_hy_month = max(hy_d3.keys()) if hy_d3 else None
        current_delta = hy_d3.get(latest_hy_month) if latest_hy_month else None
        hy_result = hySpikesToRecession(hy, current_delta=current_delta)
    return {
        "hy": hy_result,
        "yc": yieldCurveInversionsToRecession(spread_3m) if spread_3m else None,
        "ur": unemploymentBounceToRecession(ur) if ur else None,
        "cpi": cpiAccelerationEvents(cpi_raw) if cpi_raw else None,
        "sw": simultaneousWarningFlags(sw_data) if sw_data else None,
        "bull": bullishSignalFlags(sw_data) if sw_data else None,
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


def _buildDescriptionParts(risk_score: int, label: str, opp_label: str, signals: dict, events: list) -> list[str]:
    """종합 서술 조립."""
    hy_result = signals["hy"]
    yc_result = signals["yc"]
    sw_result = signals["sw"]
    bull_result = signals["bull"]
    hy_comp_result = signals["hy_comp"]

    parts: list[str] = []
    if risk_score >= 2:
        parts.append(f"위험 수준 {label} ({risk_score}점)")
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
        parts.append(f"역사적 맥락: 위험 {label}, 기회 {opp_label}")
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
    spread_3m = data.get("spread_10y3m")
    spread_2y = data.get("spread_10y2y")
    ur = data.get("unrate")
    cpi_raw = data.get("cpi_raw")
    indpro = data.get("indpro")
    vix_d = data.get("vix")
    nfci_d = data.get("nfci")

    hy_d3 = _delta_n(hy, 3) if hy else {}
    ur_d6 = _delta_n(ur, 6) if ur else {}
    ip_yoy = _yoy(indpro) if indpro else {}
    cpi_yoy = _yoy(cpi_raw) if cpi_raw else {}

    sw_data = _buildSimultaneousWarningData(hy, hy_d3, spread_2y, ur, ur_d6, vix_d, nfci_d, ip_yoy, cpi_yoy)

    signals = _computeRawSignals(hy, hy_d3, spread_3m, ur, cpi_raw, sw_data)

    event_data = dict(sw_data)
    if data.get("fedfunds"):
        event_data["fedfunds"] = data["fedfunds"]
    events = matchHistoricalEvents(event_data) if event_data else []

    risk_score = _computeRiskScore(signals)
    level, label = _riskLevelFromScore(risk_score)

    opp_score = _computeOpportunityScore(signals)
    opp_level, opp_label = _opportunityLevelFromScore(opp_score)

    desc_parts = _buildDescriptionParts(risk_score, label, opp_label, signals, events)

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
        opportunityLabel=opp_label,
        description=". ".join(desc_parts),
    )
