"""AI 오버레이 적용 — revenueForecast.py 에서 분리."""

from __future__ import annotations

import logging

from dartlab.analysis.forecast.revenueForecast import (
    RevenueForecastAIOverlay,
    RevenueForecastResult,
)

log = logging.getLogger(__name__)

_MAX_ANNUAL_ADJ = 10.0
_MAX_TOTAL_ADJ = 20.0


# ══════════════════════════════════════
# AI 오버레이 적용
# ══════════════════════════════════════


_MAX_ANNUAL_ADJ = 10.0  # 연간 보정 ±%p 캡
_MAX_TOTAL_ADJ = 20.0  # 총 보정 ±%p 캡


def applyAiOverlay(
    result: RevenueForecastResult,
    overlay: RevenueForecastAIOverlay,
) -> RevenueForecastResult:
    """AI 보정을 예측 결과에 적용.

    Capabilities:
        - AI 가설 성장률 조정 + 시나리오 확률 이동 적용
        - 연간 ±10%p · 총 ±20%p 가드레일 자동 캡

    Parameters
    ----------
    result : RevenueForecastResult
        기존 예측 결과.
    overlay : RevenueForecastAIOverlay
        AI 보정 (성장률 조정, 시나리오 확률 이동 등).

    Returns
    -------
    RevenueForecastResult
        보정 적용된 새 예측 결과.
        aiOverlay.applied = True, assumptions에 보정 요약 추가.

    Guide:
        forecastRevenue 결과에 overlay 가 있으면 마지막에 적용.

    When:
        AI 답변 단계에서 회사 맥락으로 예측 보정이 필요할 때.

    How:
        growthAdjustment 캡 적용 → 보정 시계열 재산출 → 시나리오 확률 정규화.

    Requires:
        RevenueForecastResult + RevenueForecastAIOverlay (reasoning 비어있지 않음).

    Raises:
        없음. reasoning 비어 있으면 원본 그대로 반환.

    Example:
        >>> r2 = applyAiOverlay(r, overlay)
        >>> r2.aiOverlay.applied
        True

    See Also:
        - forecastRevenue : 베이스 예측
        - RevenueForecastAIOverlay : 보정 dataclass

    AIContext:
        AI 답변 시 보정 사유 (reasoning) 와 함께 인용 — 단독 인용 금지.
    """
    if not overlay.reasoning:
        log.warning("AI overlay rejected: reasoning 비어있음")
        return result

    adj = overlay.growthAdjustment
    if not adj or len(adj) < result.horizon:
        adj = (adj or []) + [0.0] * result.horizon
        adj = adj[: result.horizon]

    # 가드레일: 연간 캡
    adj = [max(min(a, _MAX_ANNUAL_ADJ), -_MAX_ANNUAL_ADJ) for a in adj]

    # 가드레일: 총 캡
    total = sum(abs(a) for a in adj)
    if total > _MAX_TOTAL_ADJ:
        scale = _MAX_TOTAL_ADJ / total
        adj = [a * scale for a in adj]

    # 보정 적용
    newProjected: list[float] = []
    prev = (
        result.projected[0] / (1 + result.growthRates[0] / 100)
        if result.projected and result.growthRates and result.growthRates[0] != -100
        else 0
    )

    for i, (proj, gr) in enumerate(zip(result.projected, result.growthRates)):
        newGr = gr + adj[i]
        if prev > 0:
            newVal = prev * (1 + newGr / 100)
        else:
            newVal = proj * (1 + adj[i] / 100)
        newProjected.append(newVal)
        prev = newVal

    newGrowthRates = []
    for i, p in enumerate(newProjected):
        if i == 0:
            base = (
                result.projected[0] / (1 + result.growthRates[0] / 100)
                if result.projected and result.growthRates and result.growthRates[0] != -100
                else 0
            )
            if base > 0:
                newGrowthRates.append(round((p / base - 1) * 100, 1))
            else:
                newGrowthRates.append(0.0)
        elif newProjected[i - 1] > 0:
            newGrowthRates.append(round((p / newProjected[i - 1] - 1) * 100, 1))
        else:
            newGrowthRates.append(0.0)

    # 시나리오 확률 이동
    newProbs = dict(result.scenarioProbabilities)
    if overlay.scenarioShift and newProbs:
        for k, shift in overlay.scenarioShift.items():
            if k in newProbs:
                newProbs[k] = max(5, min(70, newProbs[k] + shift))
        # 정규화
        pSum = sum(newProbs.values())
        if pSum > 0:
            newProbs = {k: round(v / pSum * 100, 1) for k, v in newProbs.items()}

    appliedOverlay = RevenueForecastAIOverlay(
        growthAdjustment=adj,
        direction=overlay.direction,
        magnitude=overlay.magnitude,
        scenarioShift=overlay.scenarioShift,
        reasoning=overlay.reasoning,
        applied=True,
    )

    return RevenueForecastResult(
        historical=result.historical,
        projected=newProjected,
        horizon=result.horizon,
        method=result.method,
        confidence=overlay.confidence_override
        if hasattr(overlay, "confidence_override") and overlay.confidence_override
        else result.confidence,  # type: ignore[attr-defined]
        growthRates=newGrowthRates,
        sources=result.sources,
        sourceWeights=result.sourceWeights,
        consensusRevenue=result.consensusRevenue,
        assumptions=result.assumptions + [f"AI 보정: {overlay.direction} ({overlay.magnitude})"],
        warnings=result.warnings,
        aiContext=result.aiContext,
        scenarios=result.scenarios,
        scenarioGrowthRates=result.scenarioGrowthRates,
        scenarioProbabilities=newProbs,
        segmentForecasts=result.segmentForecasts,
        backlogSignal=result.backlogSignal,
        aiOverlay=appliedOverlay,
        forwardTestKey=result.forwardTestKey,
        currency=result.currency,
    )
