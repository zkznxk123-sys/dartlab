"""HARVEST — 세션 종료 시 메모리 자동 wiring (P-revised: propose_skill 폐기).

memory/wiring.py 공유 helper 호출 — chat-native 와 동일 SSOT.

P-revised 이전: 모델이 propose_skill tool 로 신규 skill 후보 spec 작성 → kind=generated
status=unverified 사다리. 0 promoted skill 로 dormant 상태였고 폐기됐다.
"""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.memory.wiring import wireSessionMemory
from dartlab.ai.providers import WorkbenchProvider

from .state import WorkbenchState


def runHarvest(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    """memory wiring 만 실행 (LLM 호출 없음).

    provider 인자는 시그니처 호환을 위해 유지.
    """
    yield TraceEvent(kind="pass_enter", data={"pass": "harvest"})
    _wireMemory(state)
    yield TraceEvent(kind="pass_exit", data={"pass": "harvest"})


def _wireMemory(state: WorkbenchState) -> None:
    """선택 skill 사용 통계 + 결정 회상. 실패해도 조용히."""
    from dartlab.ai.memory.wiring import inferStockCodeContext

    ok = not state.gateBlocked and state.failure is None
    stockCode, market = inferStockCodeContext(state.refs)
    if not stockCode:
        # state.profile.targets 에서도 추출 시도 (BRIEF 가 채움)
        targets = state.profile.get("targets") if isinstance(state.profile, dict) else None
        if isinstance(targets, list) and targets:
            stockCode = str(targets[0])
    extra_tags: list[str] = []
    if stockCode:
        extra_tags.append(f"target:{stockCode}")
    if market:
        extra_tags.append(f"market:{market}")

    wireSessionMemory(
        question=state.question,
        answerText=state.answerText,
        refs=state.refs,
        selectedSkillRefs=state.selectedSkillRefs,
        ok=ok,
        runId=state.runId,
        extraTags=extra_tags,
    )
