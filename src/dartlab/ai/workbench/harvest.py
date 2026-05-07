"""HARVEST — 세션 종료 시 메모리 자동 wiring (P-revised: propose_skill 폐기).

세션 종료 시:
- 선택된 skill 별로 recordSkillUsage() — usage 통계 누적
- 답변 요약을 remember() 로 decisions.jsonl 에 저장 — 다음 세션 recall

P-revised 이전: LLM 이 propose_skill tool 로 신규 skill 후보 spec 작성 → kind=generated
status=unverified 사다리. 0 promoted skill 로 dormant 상태였고 outcome ground truth loop 가
실용적 학습 신호로 대체.
"""

from __future__ import annotations

from collections.abc import Iterator

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.memory import recordSkillUsage, remember
from dartlab.ai.providers import WorkbenchProvider

from .state import WorkbenchState


def runHarvest(state: WorkbenchState, provider: WorkbenchProvider) -> Iterator[TraceEvent]:
    """P-revised: LLM 패스 호출 없이 memory wiring 만 실행.

    provider 인자는 시그니처 호환을 위해 유지. 향후 outcome_log resolve hook 도입 시 사용.
    """
    yield TraceEvent(kind="pass_enter", data={"pass": "harvest"})
    _wireMemory(state)
    yield TraceEvent(kind="pass_exit", data={"pass": "harvest"})


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
