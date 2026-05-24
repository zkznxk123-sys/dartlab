"""recipe 자동 승급 조건 (T5-3) — coverage + mutation 기반 자동 전이.

T5-3 트랙: drafted → tested 자동 조건 정의. CLAUDE.md `feedback_recipe_lifecycle`
정합 — *AI/도구 자동 변경 금지* + *사용자 manual override 가능* 룰 준수.
본 모듈은 *조건 평가만 수행*. 실제 status frontmatter 변경은 운영자가 수동으로.

자동 승급 조건 (drafted → tested):
    1. 해당 recipe 의 unit test 커버리지 ≥ 90 percent
    2. 해당 recipe mutation score ≥ 80 percent (mutmut)
    3. 24h 안 PR fail 0 건

자동 승급 조건 (tested → verified):
    1. 30 일 incidents 0 건
    2. 사용자 명시 OK (manual gate)

사용자 manual override:
    스크립트 결과는 *제안* 일 뿐. 운영자가 `recipePromote.py` CLI 로 최종 확정.

실행::

    >>> from dartlab.skills.recipePromotion import evaluatePromotion
    >>> result = evaluatePromotion(
    ...     recipeName="foreignBuyMomentum",
    ...     currentStage="drafted",
    ...     coverage=92.5,
    ...     mutationScore=85.0,
    ...     prFailIn24h=0,
    ... )
    >>> result
    {'recommended': True, 'targetStage': 'tested', 'reason': '3 조건 모두 통과'}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RecipeStage = Literal["drafted", "unverified", "tested", "verified", "curated", "deprecated"]


@dataclass
class PromotionEvaluation:
    """recipe 승급 평가 결과 — 사용자 의사결정 입력."""

    recommended: bool
    targetStage: RecipeStage | None
    reason: str
    failedConditions: list[str] = field(default_factory=list)
    metrics: dict[str, object] = field(default_factory=dict)


# 단계별 자동 승급 조건 정의.
_DRAFTED_TO_TESTED: dict[str, tuple[float, str]] = {
    "coverage": (90.0, "unit test 커버리지 ≥ 90 percent"),
    "mutationScore": (80.0, "mutation score ≥ 80 percent (mutmut)"),
    "prFailIn24h": (0.0, "24h 안 PR fail 0 건"),  # 작거나 같음 (역방향)
}


_TESTED_TO_VERIFIED: dict[str, tuple[float, str]] = {
    "incidentsIn30Days": (0.0, "30 일 incidents 0 건"),  # 작거나 같음
    "userManualOk": (1.0, "사용자 명시 OK (manual gate)"),
}


def evaluatePromotion(
    recipeName: str,
    currentStage: RecipeStage,
    *,
    coverage: float | None = None,
    mutationScore: float | None = None,
    prFailIn24h: int | None = None,
    incidentsIn30Days: int | None = None,
    userManualOk: bool = False,
) -> PromotionEvaluation:
    """자동 승급 조건 평가 — 사용자 의사결정 입력.

    Args:
        recipeName: 평가 대상 recipe 이름 (예: "foreignBuyMomentum").
        currentStage: 현재 단계.
        coverage: unit test 커버리지 percent.
        mutationScore: mutmut 결과 percent.
        prFailIn24h: 최근 24h 안 PR fail 횟수.
        incidentsIn30Days: 30 일 incidents 누적 건수.
        userManualOk: 사용자 manual OK 여부.
    Returns:
        PromotionEvaluation — recommended 여부 + 사유.
    """
    if currentStage == "drafted":
        return _evaluateDraftedToTested(
            recipeName,
            coverage=coverage,
            mutationScore=mutationScore,
            prFailIn24h=prFailIn24h,
        )
    if currentStage == "tested":
        return _evaluateTestedToVerified(
            recipeName,
            incidentsIn30Days=incidentsIn30Days,
            userManualOk=userManualOk,
        )
    return PromotionEvaluation(
        recommended=False,
        targetStage=None,
        reason=f"현재 단계 '{currentStage}' 는 자동 승급 대상 아님",
    )


def _evaluateDraftedToTested(
    recipeName: str,
    *,
    coverage: float | None,
    mutationScore: float | None,
    prFailIn24h: int | None,
) -> PromotionEvaluation:
    """drafted → tested 조건 3 종 평가."""
    metrics: dict[str, object] = {
        "coverage": coverage,
        "mutationScore": mutationScore,
        "prFailIn24h": prFailIn24h,
    }
    failed: list[str] = []
    if coverage is None or coverage < _DRAFTED_TO_TESTED["coverage"][0]:
        failed.append(f"coverage {coverage} (필요 {_DRAFTED_TO_TESTED['coverage'][0]})")
    if mutationScore is None or mutationScore < _DRAFTED_TO_TESTED["mutationScore"][0]:
        failed.append(f"mutationScore {mutationScore} (필요 {_DRAFTED_TO_TESTED['mutationScore'][0]})")
    if prFailIn24h is None or prFailIn24h > _DRAFTED_TO_TESTED["prFailIn24h"][0]:
        failed.append(f"prFailIn24h {prFailIn24h} (필요 ≤ {_DRAFTED_TO_TESTED['prFailIn24h'][0]:.0f})")

    if not failed:
        return PromotionEvaluation(
            recommended=True,
            targetStage="tested",
            reason="3 조건 모두 통과",
            metrics=metrics,
        )
    return PromotionEvaluation(
        recommended=False,
        targetStage="tested",
        reason="조건 미달",
        failedConditions=failed,
        metrics=metrics,
    )


def _evaluateTestedToVerified(
    recipeName: str,
    *,
    incidentsIn30Days: int | None,
    userManualOk: bool,
) -> PromotionEvaluation:
    """tested → verified 조건 2 종 평가."""
    metrics: dict[str, object] = {
        "incidentsIn30Days": incidentsIn30Days,
        "userManualOk": userManualOk,
    }
    failed: list[str] = []
    if incidentsIn30Days is None or incidentsIn30Days > _TESTED_TO_VERIFIED["incidentsIn30Days"][0]:
        failed.append(f"incidentsIn30Days {incidentsIn30Days} (필요 ≤ 0)")
    if not userManualOk:
        failed.append("userManualOk 미부여 (manual gate 필수)")

    if not failed:
        return PromotionEvaluation(
            recommended=True,
            targetStage="verified",
            reason="2 조건 모두 통과 (사용자 manual OK 포함)",
            metrics=metrics,
        )
    return PromotionEvaluation(
        recommended=False,
        targetStage="verified",
        reason="조건 미달",
        failedConditions=failed,
        metrics=metrics,
    )


__all__ = ["RecipeStage", "PromotionEvaluation", "evaluatePromotion"]
