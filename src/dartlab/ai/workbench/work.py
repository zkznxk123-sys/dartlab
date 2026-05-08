"""WORK — RunPython / InspectDataset / EngineCall / WebSearch / SaveArtifact 반복.

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
from .targets import _hasRecipe


def runWork(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    yield from runLLMPass(
        state,
        provider,
        passName="work",
        systemPrompt=WORK_PROMPT,
        userContext=buildContextSummary(state),
        allowedTools=[
            "RunPython",
            "InspectDataset",
            "EngineCall",
            "WebSearch",
            "SaveArtifact",
        ],
        maxRounds=_inferWorkRounds(state),
        role="analysis",
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
