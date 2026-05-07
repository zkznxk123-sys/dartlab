"""5 패스 LLM-driven 작업대 — BRIEF → WORK → CRITIQUE → COMPOSE → GATE → HARVEST.

분석 의도 명시 시 loop.stream() 가 본 모듈로 라우팅. tool 호출은 work.py 의
도구 루프 안에서 일어나며, GATE 차단 시 WORK 회귀 (recipe 활성이면 최대 3 회).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import TraceEvent

from .brief import runBrief
from .compose import runCompose
from .critique import runCritique
from .gate import runGate
from .harvest import runHarvest
from .state import WorkbenchState
from .targets import _hasRecipe
from .work import runWork


def streamLLMPasses(
    question: str, provider: Any, *, graphNodes: tuple[str, ...], **kwargs: Any
) -> Iterator[TraceEvent]:
    state = WorkbenchState(
        question=str(question or "").strip(),
        threadId=str(kwargs.get("threadId") or ""),
    )

    yield TraceEvent("graph_node", {"node": "brief", "status": "running"})
    yield from runBrief(state, provider)

    yield TraceEvent("graph_node", {"node": "work", "status": "running"})
    yield from runWork(state, provider)

    yield TraceEvent("graph_node", {"node": "critique", "status": "running"})
    yield from runCritique(state, provider)

    yield TraceEvent("graph_node", {"node": "compose", "status": "running"})
    yield from runCompose(state, provider)

    yield TraceEvent("graph_node", {"node": "gate", "status": "running"})
    yield from runGate(state)

    # GATE 차단 시 WORK 회귀. recipe 활성이면 최대 3 회, 아니면 2 회.
    # rate_limit / 외부 provider 실패는 retry 의미 없으므로 즉시 종료.
    max_iter = 3 if _hasRecipe(state) else 2
    while state.gateBlocked and state.iteration < max_iter and state.failure != "rate_limit":
        state.iteration += 1
        yield TraceEvent("graph_node", {"node": "work", "status": "running", "round": state.iteration})
        yield from runWork(state, provider)
        yield TraceEvent("graph_node", {"node": "compose", "status": "running", "round": state.iteration})
        yield from runCompose(state, provider)
        yield TraceEvent("graph_node", {"node": "gate", "status": "running", "round": state.iteration})
        yield from runGate(state)

    yield TraceEvent("graph_node", {"node": "harvest", "status": "running"})
    yield from runHarvest(state, provider)

    answer = state.answerText or "응답 생성 실패"
    if state.failure == "rate_limit":
        answer = (
            "외부 LLM provider (ChatGPT OAuth) 의 요청 한도가 초과되어 답변을 생성하지 못했습니다. "
            "잠시 후 (보통 수 분 ~ 1 시간) 자동 회복됩니다. 즉시 진행하려면 다른 provider "
            "(openai / gemini / ollama 등) 로 전환하세요."
        )
        state.status = "rate_limited"
    elif state.gateBlocked:
        issues = "; ".join(state.gateIssues)
        answer = f"{answer}\n\n[GATE 미통과 — 추가 검증 필요: {issues}]"
        state.status = "gate_blocked"
    else:
        state.status = "done"

    yield TraceEvent("answer", {"text": answer, "evidenceRefs": [r.id for r in state.refs]})
    for chunk in _chunks(answer):
        yield TraceEvent("chunk", {"text": chunk})
    yield TraceEvent(
        "done",
        {
            "refs": [r.to_dict() for r in state.refs],
            "evidence": [r.to_dict() for r in state.refs if r.kind != "verifyRef"],
            "claims": list(state.claims),
            "artifacts": [r.to_dict() for r in state.refs if r.kind == "artifactRef"],
            "verification": state.verification,
            "responseMeta": {
                "finalEvent": "answer",
                "responseStatus": "ok" if state.status == "done" else "failed",
                "refCount": len(state.refs),
                "passes": list(graphNodes),
            },
        },
    )


def _chunks(text: str, *, size: int = 240) -> Iterator[str]:
    for index in range(0, len(text), size):
        yield text[index : index + size]
