"""WORK — run_python / inspect_dataset / engine_call / web_search / save_artifact 반복.

maxRounds 동적:
- recipe 활성 → 12 (다단 분석)
- 단순 (skill 1 + targets ≤ 1 + lens 비활성) → 4
- 그 외 → 8 (default)
"""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import WorkbenchProvider

from .prompts import WORK_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runWork(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    yield from runLLMPass(
        state,
        provider,
        passName="work",
        systemPrompt=WORK_PROMPT,
        userContext=buildContextSummary(state),
        allowedTools=[
            "run_python",
            "inspect_dataset",
            "engine_call",
            "web_search",
            "save_artifact",
        ],
        maxRounds=_inferWorkRounds(state),
    )


def _inferWorkRounds(state: WorkbenchState) -> int:
    """질문 난이도별 maxRounds.

    - recipe 활성 → 12
    - 단순 (selectedSkillRefs 1 개 + targets ≤ 1 + activeLenses 비어있음) → 4
    - 그 외 → 8 (default)
    """
    if _hasRecipe(state):
        return 12
    targets = list(state.profile.get("targets") or [])
    active_lenses = list(state.profile.get("activeLenses") or [])
    if len(state.selectedSkillRefs) <= 1 and len(targets) <= 1 and not active_lenses:
        return 4
    return 8


def _hasRecipe(state: WorkbenchState) -> bool:
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        if payload.get("kind") == "recipe" or payload.get("recipeSteps"):
            return True
    return False
