"""CRITIQUE — 반대가설 / 누락 lens 점검."""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import WorkbenchProvider

from .prompts import CRITIQUE_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runCritique(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    text_collector: list[str] = []
    for ev in runLLMPass(
        state,
        provider,
        passName="critique",
        systemPrompt=CRITIQUE_PROMPT,
        userContext=buildContextSummary(state),
        allowedTools=[],
        maxRounds=2,
    ):
        if ev.kind == "llm_text":
            text_collector.append(ev.data.get("text", ""))
        yield ev

    text = "".join(text_collector).strip()
    if text:
        state.critiques.append({"text": text})
