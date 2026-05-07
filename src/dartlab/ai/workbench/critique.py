"""CRITIQUE — 반대가설 + 선택 skill 의 requiredEvidence 동적 체크리스트."""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.providers import WorkbenchProvider

from .prompts import CRITIQUE_PROMPT
from .runner import buildContextSummary, runLLMPass
from .state import WorkbenchState


def runCritique(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    user_ctx = _buildCritiqueContext(state)
    text_collector: list[str] = []
    for ev in runLLMPass(
        state,
        provider,
        passName="critique",
        systemPrompt=CRITIQUE_PROMPT,
        userContext=user_ctx,
        allowedTools=[],
        maxRounds=2,
        role="analysis",
    ):
        if ev.kind == "llm_text":
            text_collector.append(ev.data.get("text", ""))
        yield ev

    text = "".join(text_collector).strip()
    if text:
        state.critiques.append({"text": text})


def _buildCritiqueContext(state: WorkbenchState) -> str:
    """기본 컨텍스트 + 선택 skill 의 requiredEvidence 명시 체크리스트."""
    parts = [buildContextSummary(state)]
    required = _collectRequiredEvidence(state)
    if required:
        bullet_lines = "\n".join(f"- {item}" for item in required)
        parts.append(
            "선택 skill 의 requiredEvidence 체크리스트 (이 항목들이 답변에서 충족됐는지 확인):\n" + bullet_lines
        )
    return "\n\n".join(parts)


def _collectRequiredEvidence(state: WorkbenchState) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in state.requiredEvidence:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    for ref in state.selectedSkillRefs:
        payload = ref.payload if isinstance(ref.payload, dict) else {}
        for item in payload.get("requiredEvidence") or []:
            sval = str(item)
            if sval and sval not in seen:
                seen.add(sval)
                out.append(sval)
    return out
