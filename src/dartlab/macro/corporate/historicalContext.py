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

# 이벤트 통계 (분리: _historicalContextEvents.py SSOT, re-export 으로 BC 보존)
from dartlab.macro.corporate._historicalContextEvents import (  # noqa: F401
    cpiAccelerationEvents,
    hySpikesToRecession,
    simultaneousWarningFlags,
    unemploymentBounceToRecession,
    yieldCurveInversionsToRecession,
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
