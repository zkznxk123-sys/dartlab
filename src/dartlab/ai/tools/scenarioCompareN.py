"""ScenarioCompareN — 다중 macro 시나리오 동시 비교 (baseline vs N).

마스터 플랜 트랙 1 PR-5 (cryptic-discovering-kettle.md). macro.scenarios.engine.
compareScenarios wrap — N 시나리오 baseline 대비 score/cycle/crisis 변화량 한 도구
호출로 답변. RunPython loop 우회 회귀 차단.

신뢰도 35 (scenario method) — assumptions 다중 누적.

graph 회귀 방지: agent.py 본체·노드 추가 0. LLM 자율 호출 도구.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.contracts import Ref
from dartlab.core.confidence import baseScore

from .types import ToolResult


def scenarioCompareN(
    scenarioNames: list[str] | None = None,
    severity: str | None = None,
    market: str = "US",
) -> ToolResult:
    """N 시나리오 baseline 대비 비교.

    Capabilities:
        macro.scenarios.engine.compareScenarios wrap. N (2~5) 시나리오 각각 baseline
        대비 score_delta + cycle_phase + crisis_zone + transmission 비교 테이블.

    Parameters
    ----------
    scenarioNames : list[str]
        2~5 시나리오 이름 (예: ['2008 금융위기', '금리 충격', 'asia_crisis']).
    severity : str | None
        모든 시나리오 공통 심각도 ('mild'/'moderate'/'severe'/'extreme'). preset 별 지원.
    market : str
        'US' or 'KR'. 기본 'US'.

    Returns
    -------
    ToolResult
        - data.baseline : {score, overall}
        - data.scenarios : dict[name → 단일 시나리오 결과]
        - data.comparison : list[dict] — score_delta 정렬됨
        - data.market : str
        - data.confidence : 35 (scenario method)
        - refs : executionRef × N + tableRef (comparison)

    Example
    -------
        ScenarioCompareN(scenarioNames=["2008 금융위기", "금리 충격"], market="US")

    Raises
    ------
    없음 — 시나리오 매칭 실패는 skip + warning, 전부 실패 시 error.

    Guide
    -----
        score_delta 가 가장 음수 = 최악 케이스. crisis_zone 변화 동반 시 위기 신호.

    SeeAlso
    -------
        - scenarioOverlay : 단일 시나리오 + 종목 임팩트
        - macro.scenarios.engine.compareScenarios : 본 도구가 호출
        - macro.scenarios.engine.listAllScenarios : 시나리오 카탈로그

    Requires
    --------
        매크로 provider 활성 (FRED/ECOS). analyzeSummary 1+N 회 호출.

    AIContext
    ---------
        "여러 시나리오 비교", "스트레스 테스트", "최악 케이스" 류 질문에 본 도구
        호출. comparison 정렬 후 최악/최선 시나리오 1~2 건 + score_delta 답변 인용.

    LLM Specifications
    ------------------
        AntiPatterns:
            - scenarioNames=[1개만] — 단일 시나리오는 ScenarioOverlay 사용.
            - 시나리오 5+ 개 동시 (FRED rate limit + polars 힙 압박).
        OutputSchema:
            comparison[i] = {scenario, severity, type, score, score_delta, overall,
            cycle_phase, crisis_zone, transmission, outcome}.
        Prerequisites:
            매크로 provider 활성.
        Freshness:
            baseline real-time.
        Dataflow:
            baseline → 시나리오 N 회 → comparison 정렬 → ref.
        TargetMarkets:
            US, KR.
    """
    if not scenarioNames or not isinstance(scenarioNames, list):
        return ToolResult(
            False,
            "scenarioNames 필수 (2~5 시나리오).",
            error="missing_scenario_names",
        )
    names = [str(n).strip() for n in scenarioNames if str(n).strip()]
    if len(names) < 2:
        return ToolResult(
            False,
            "scenarioNames 2~5 개 필수. 단일은 ScenarioOverlay 사용.",
            error="insufficient_scenarios",
        )
    if len(names) > 5:
        names = names[:5]

    market_norm = market if market in ("US", "KR") else "US"

    try:
        from dartlab.macro.scenarios.engine import compareScenarios

        result = compareScenarios(names, severity=severity, market=market_norm)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(
            False,
            f"compareScenarios 실패: {type(exc).__name__}: {exc}",
            error="compare_failed",
        )

    if not result or not result.get("comparison"):
        return ToolResult(
            False,
            "comparison 결과 비어있음 — 모든 시나리오 매칭 실패.",
            error="all_scenarios_unmatched",
        )

    # score_delta 정렬 (오름차순 — 가장 음수 = 최악)
    comparison_sorted = sorted(result["comparison"], key=lambda c: c.get("score_delta", 0.0))
    confidence = baseScore("scenario")

    payload: dict[str, Any] = {
        "baseline": result.get("baseline", {}),
        "scenarios": result.get("scenarios", {}),
        "comparison": comparison_sorted,
        "market": market_norm,
        "severity": severity,
        "confidence": confidence,
        "confidenceMethod": "scenario",
    }

    refs: list[Ref] = []
    for c in comparison_sorted:
        name = c.get("scenario", "?")
        refs.append(
            Ref(
                id=f"scenarioCmp:{market_norm}:{name}",
                kind="executionRef",
                title=f"{name} (Δscore={c.get('score_delta', 0):+.2f})",
                source="scenarioCompareN",
                payload={
                    "scenarioId": name,
                    "severity": c.get("severity"),
                    "scoreDelta": c.get("score_delta"),
                    "cyclePhase": c.get("cycle_phase"),
                    "crisisZone": c.get("crisis_zone"),
                    "transmission": c.get("transmission"),
                    "outcome": c.get("outcome"),
                    "market": market_norm,
                    "confidence": confidence,
                },
            )
        )
    refs.append(
        Ref(
            id=f"scenarioCmp:{market_norm}:matrix",
            kind="tableRef",
            title=f"{len(names)} 시나리오 비교 matrix ({market_norm})",
            source="scenarioCompareN",
            payload=payload,
        )
    )

    worst = comparison_sorted[0] if comparison_sorted else {}
    best = comparison_sorted[-1] if comparison_sorted else {}
    summary = (
        f"{len(names)} 시나리오 비교 ({market_norm}) — "
        f"최악: {worst.get('scenario', '?')} Δ{worst.get('score_delta', 0):+.2f} · "
        f"최선: {best.get('scenario', '?')} Δ{best.get('score_delta', 0):+.2f}"
    )
    return ToolResult(True, summary, refs=refs, data=payload)


__all__ = ["scenarioCompareN"]
