"""COMPOSE — 답안 + ref 묶음."""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import WorkbenchProvider

from .prompts import COMPOSE_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runCompose(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    """runCompose — TODO 한국어 동작 설명."""
    text_collector: list[str] = []
    for ev in runLLMPass(
        state,
        provider,
        passName="compose",
        systemPrompt=COMPOSE_PROMPT,
        userContext=buildContextSummary(state),
        allowedTools=[],
        maxRounds=2,
        role="analysis",
    ):
        if ev.kind == "llm_text":
            text_collector.append(ev.data.get("text", ""))
        yield ev

    state.answerText = "".join(text_collector).strip()
