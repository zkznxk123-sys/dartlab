"""HARVEST — trace 보고 propose_skill 후보 결정 + 메모리 자동 wiring.

세션 종료 시:
- 선택된 skill 별로 recordSkillUsage() — promotion 통계 누적
- 답변 요약을 remember() 로 decisions.jsonl 에 저장 — 다음 세션 recall
"""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.memory import recordSkillUsage, remember
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

    _wireMemory(state)


def _wireMemory(state: WorkbenchState) -> None:
    """선택 skill 사용 통계 + 결정 회상 자동 기록. 실패해도 조용히."""
    ok = not state.gateBlocked and state.failure is None
    value_refs = sum(1 for r in state.refs if r.kind == "valueRef")

    for ref in state.selectedSkillRefs:
        skill_id = (ref.payload or {}).get("id") or ref.id.removeprefix("skill:")
        if not skill_id:
            continue
        try:
            recordSkillUsage(str(skill_id), ok=ok, valueRefs=value_refs)
        except Exception:  # noqa: BLE001
            pass

    if not state.answerText:
        return
    digest = state.answerText[:280].replace("\n", " ").strip()
    if not digest:
        return
    tags = ["pass:harvest", f"runId:{state.runId}", f"status:{'ok' if ok else 'failed'}"]
    for ref in state.selectedSkillRefs[:3]:
        skill_id = (ref.payload or {}).get("id") or ref.id.removeprefix("skill:")
        if skill_id:
            tags.append(f"skill:{skill_id}")
    try:
        remember(f"Q: {state.question[:200]}\nA: {digest}", tags=tags)
    except Exception:  # noqa: BLE001
        pass
