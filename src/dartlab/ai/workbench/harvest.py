"""HARVEST — trace 보고 propose_skill 후보 결정."""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import WorkbenchProvider

from .prompts import HARVEST_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runHarvest(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    yield from runLLMPass(
        state,
        provider,
        passName="harvest",
        systemPrompt=HARVEST_PROMPT,
        userContext=buildContextSummary(state),
        allowedTools=["propose_skill"],
        maxRounds=2,
    )

    for call in state.toolCalls:
        if call.get("pass") == "harvest" and call.get("tool") == "propose_skill" and call.get("ok"):
            state.harvestProposals.append({"args": call.get("args")})
