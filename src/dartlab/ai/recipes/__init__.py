"""Recipe lifecycle support — chat-native, stateless 모듈만.

`feedback_no_graph_regression.md` 강행규칙: BRIEF/WORK/CRITIQUE/COMPOSE/GATE/HARVEST 식 phase
체인 도입 금지. 본 패키지는 모두 stateless 함수 — `validateRefs`, `appendRun`, `computeScorecard`,
`detectDrift`. AI tool (`ValidateRecipe` 등) 이 호출하는 plain library.

자기개선 사다리 (status frontmatter 자동 변경) 도입 금지. status 디스크 쓰기는 항상 운영자
CLI (`src/dartlab/skills/recipePromote.py`) 단독 권한. 본 패키지는 read-only + append-only run 기록만.
"""

from __future__ import annotations

from .drift import DriftReport, detectDrift
from .runs import RECIPE_RUNS_DIR, RecipeRunRecord, appendRun, loadRuns
from .scorecard import RecipeScorecard, ScorecardThresholds, computeScorecard
from .validate import RefValidationResult, validateRefs

__all__ = [
    "RECIPE_RUNS_DIR",
    "DriftReport",
    "RecipeRunRecord",
    "RecipeScorecard",
    "RefValidationResult",
    "ScorecardThresholds",
    "appendRun",
    "computeScorecard",
    "detectDrift",
    "loadRuns",
    "validateRefs",
]
