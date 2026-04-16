"""FeedbackLoopAgent — Damodaran 6단계 자동 루프 (Phase 10 G8).

Narrative ↔ Numbers feedback:
  1. 현재 narrative (causalWeights)
  2. 현재 DCF (baseline dFV)
  3. 신규 이벤트/가정 → overrides
  4. scenario dFV
  5. narrative diff → 충돌 감지
  6. trajectory 재생성 → 가치 diff 타임라인
"""

from __future__ import annotations

from typing import Any


def runFeedbackCycle(
    company: Any,
    *,
    newEvent: str | None = None,
    eventOverrides: dict | None = None,
    basePeriod: str | None = None,
) -> dict:
    """Damodaran 6단계 자동 루프.

    Parameters
    ----------
    company : Company
    newEvent : str — 이벤트 요약 (narrate 용)
    eventOverrides : dict — 이벤트가 유발하는 override
    basePeriod : 기준 기간

    Returns
    -------
    dict
        step1_narrative : 현재 인과 체인 (causalWeights)
        step2_baseline : 기준 dFV
        step3_event : 이벤트 description
        step4_scenario : scenario dFV + overrides
        step5_diff : delta_abs/delta_pct/narrativeShift
        step6_trajectory : 3 trajectory 갱신
    """
    from dartlab.review.narrative import buildCausalWeights, buildValuationImpact
    from dartlab.review.storyTree import buildStoryTree
    from dartlab.review.counterfactual import runCounterfactual

    # Step 1: 현재 narrative
    chains = buildCausalWeights(company, {})

    # Step 2: baseline
    from dartlab.analysis.valuation.dFV import calcDFV
    baseline = calcDFV(company, basePeriod=basePeriod)
    baseline_dfv = baseline.get("dFV") if baseline else None

    # Step 3: 이벤트 적용
    event_str = newEvent or "(이벤트 없음 — baseline 상태 진단)"
    overrides = eventOverrides or {}

    # Step 4: scenario (overrides 있을 때만)
    if overrides:
        counter = runCounterfactual(company, overrides=overrides, basePeriod=basePeriod)
        scenario_dfv = counter.get("scenario", {}).get("dFV")
    else:
        counter = None
        scenario_dfv = baseline_dfv

    # Step 5: diff
    delta_abs = (scenario_dfv - baseline_dfv) if (scenario_dfv and baseline_dfv) else 0
    delta_pct = (delta_abs / baseline_dfv * 100) if baseline_dfv else 0

    # narrative shift — 인과 방향이 바뀌었는지 정성 판단
    narrative_shift = "중립" if abs(delta_pct) < 5 else ("상향" if delta_pct > 0 else "하향")

    # Step 6: trajectory 재생성 (scenario 기준)
    trajectory = buildStoryTree(company, basePeriod=basePeriod)

    # valuationImpact — AI override 힌트
    impact = buildValuationImpact(chains)

    return {
        "step1_narrative": {
            "chains": chains,
            "impact": impact,
        },
        "step2_baseline": {
            "dFV": baseline_dfv,
        },
        "step3_event": event_str,
        "step4_scenario": {
            "dFV": scenario_dfv,
            "overrides": overrides,
            "counter": counter,
        },
        "step5_diff": {
            "delta_abs": round(delta_abs, 0) if delta_abs else 0,
            "delta_pct": round(delta_pct, 2),
            "narrativeShift": narrative_shift,
        },
        "step6_trajectory": trajectory,
    }
