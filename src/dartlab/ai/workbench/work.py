"""WORK — run_python / web_search / save_artifact 반복."""

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
        maxRounds=8,
    )
