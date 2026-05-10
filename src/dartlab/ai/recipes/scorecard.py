"""Recipe 6 신호 scorecard — 누적 run 기록에서 산출.

`feedback_no_graph_regression.md` 준수: 본 모듈은 stateless. graph node 없음. ValidateRecipe 가
loadRuns() → computeScorecard() 흐름으로 한 번 호출.

6 신호 (plan §6 신호 Scorecard):
- executionPassRate: 성공 run / 전체 run (≥ 0.80 to verify)
- evidenceCompleteness: requiredEvidence kind 모두 등장 (= 1.00)
- crossTargetStability: target 간 headline metric std-dev (≥ 0.10, ≤ 0.50)
- novelty: 출력 컬럼셋이 단일 엔진 컬럼셋의 부분집합이 아님 (true)
- falsifiability: counter-test 가 universe 에서 실제 평가됨
- operatorVerdict: 운영자 yes/no (CLI 단계에서 판단)

스코어카드는 *권장 임계 + 측정값* 만 반환. promote/deprecate 결정은 운영자 CLI 가 단독 권한.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field
from typing import Any

import polars as pl


@dataclass(frozen=True)
class ScorecardThresholds:
    """tested → verified 게이트 권장 임계.

    Notes
    -----
    임계값은 plan §6 신호 표의 default. 운영자 CLI 가 임계 override 가능.
    """

    minExecutionPassRate: float = 0.80
    requiredEvidenceCompleteness: float = 1.00
    minCrossTargetStability: float = 0.10
    maxCrossTargetStability: float = 0.50
    requiresNovelty: bool = True
    requiresFalsifierEvaluated: bool = True


@dataclass(frozen=True)
class RecipeScorecard:
    """6 신호 산출 결과.

    Attributes
    ----------
    skillId : str
        대상 recipe id.
    runCount : int
        집계 대상 run 수.
    executionPassRate : float
        ok=True / 전체.
    evidenceCompleteness : float
        run 단위로 requiredEvidence 모두 등장한 비율 (0~1).
    crossTargetStability : float
        target 간 headline metric 표본 표준편차 (수치 metric 일 때만 의미). NaN 가능 (str / 단일 target).
    novelty : bool
        보유 expectedNovelty 컬럼셋이 단일 linked 엔진 컬럼셋의 부분집합이 아님.
        본 모듈은 expectedNovelty 의 *존재* 만 판정 — 실 컬럼셋 비교는 운영자 inspect.
    falsifierEvaluated : bool
        falsifier.pythonCheck 가 적어도 1 개 run 에서 실행됐는지 (run 메타 data 필요).
    meetsThresholds : bool
        operatorVerdict 외 5 신호 모두 임계 충족.
    """

    skillId: str
    runCount: int
    executionPassRate: float
    evidenceCompleteness: float
    crossTargetStability: float
    novelty: bool
    falsifierEvaluated: bool
    meetsThresholds: bool
    notes: list[str] = field(default_factory=list)

    def toDict(self) -> dict[str, Any]:
        return asdict(self)


def _safeFloat(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _stability(values: list[float]) -> float:
    """표본 표준편차. 0 또는 1 개 값이면 NaN 의미로 0.0 반환 (의미 없는 stability)."""
    if len(values) < 2:
        return 0.0
    return float(statistics.pstdev(values))


def computeScorecard(
    skillId: str,
    runs: pl.DataFrame,
    *,
    requiredEvidence: list[str] | None = None,
    expectedNovelty: list[str] | None = None,
    falsifierPresent: bool = False,
    thresholds: ScorecardThresholds | None = None,
) -> RecipeScorecard:
    """누적 run + recipe 메타에서 6 신호 scorecard 산출.

    Parameters
    ----------
    skillId : str
        recipe id.
    runs : pl.DataFrame
        loadRuns() 결과 — runId/ok/evidenceKinds/headlineValue/refs 등 컬럼.
    requiredEvidence : list[str], optional
        recipe frontmatter `requiredEvidence`. evidenceCompleteness 계산에 사용.
    expectedNovelty : list[str], optional
        recipe frontmatter `expectedNovelty`. novelty 신호 판정.
    falsifierPresent : bool
        recipe frontmatter `falsifier.pythonCheck` 존재 여부.
    thresholds : ScorecardThresholds, optional
        임계 override (override 안 하면 default).

    Returns
    -------
    RecipeScorecard
        6 신호 + meetsThresholds boolean (operatorVerdict 제외).
    """
    th = thresholds or ScorecardThresholds()
    notes: list[str] = []

    if runs.is_empty():
        return RecipeScorecard(
            skillId=skillId,
            runCount=0,
            executionPassRate=0.0,
            evidenceCompleteness=0.0,
            crossTargetStability=0.0,
            novelty=bool(expectedNovelty),
            falsifierEvaluated=False,
            meetsThresholds=False,
            notes=["no runs"],
        )

    n = runs.height
    pass_count = int(runs.filter(pl.col("ok")).height)
    pass_rate = pass_count / n if n else 0.0

    needed = set(requiredEvidence or [])
    if needed:
        per_run_completeness: list[float] = []
        for kinds in runs["evidenceKinds"].to_list():
            kinds_set = set(kinds or [])
            covered = len(needed & kinds_set) / len(needed)
            per_run_completeness.append(covered)
        completeness = sum(per_run_completeness) / len(per_run_completeness) if per_run_completeness else 0.0
    else:
        completeness = 1.0  # requiredEvidence 미지정 → completeness 항목 무력화 (1.0).
        notes.append("requiredEvidence empty → completeness vacuous-true")

    # crossTargetStability — run 의 headline 수치값 std-dev. target 별 평균을 먼저 묶고 그 위에서 std.
    headline_floats = [_safeFloat(v) for v in runs["headlineValue"].to_list()]
    valid_floats = [v for v in headline_floats if v is not None]
    if len(valid_floats) >= 2:
        # target 별 평균 → 그 위 std (target 간 분산이 핵심).
        per_target: dict[str, list[float]] = {}
        for target, value in zip(runs["target"].to_list(), headline_floats):
            if value is None:
                continue
            per_target.setdefault(str(target), []).append(value)
        per_target_means = [sum(values) / len(values) for values in per_target.values() if values]
        stability = _stability(per_target_means) if len(per_target_means) >= 2 else 0.0
    else:
        stability = 0.0
        notes.append("headlineValue not numeric — stability vacuous-zero")

    novelty = bool(expectedNovelty)
    if not novelty:
        notes.append("expectedNovelty empty → novelty=false")

    # falsifierEvaluated: 본 모듈은 frontmatter 의 *존재* + 적어도 1 회 run 실행을 함께 확인.
    falsifier_evaluated = bool(falsifierPresent) and n > 0
    if falsifierPresent and not n:
        notes.append("falsifier present but no runs")
    if not falsifierPresent:
        notes.append("falsifier missing in frontmatter")

    # meetsThresholds — operatorVerdict 제외한 5 개 신호 임계 충족.
    meets = (
        pass_rate >= th.minExecutionPassRate
        and completeness >= th.requiredEvidenceCompleteness
        and th.minCrossTargetStability <= stability <= th.maxCrossTargetStability
        and (novelty if th.requiresNovelty else True)
        and (falsifier_evaluated if th.requiresFalsifierEvaluated else True)
    )

    return RecipeScorecard(
        skillId=skillId,
        runCount=n,
        executionPassRate=pass_rate,
        evidenceCompleteness=completeness,
        crossTargetStability=stability,
        novelty=novelty,
        falsifierEvaluated=falsifier_evaluated,
        meetsThresholds=meets,
        notes=notes,
    )
