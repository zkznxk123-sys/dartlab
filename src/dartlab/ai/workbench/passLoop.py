"""PassLoop — 5 패스 작업대 orchestration.

진입은 `kernel.py::ask()` 가 provider 가 dartlab 가 아닐 때 본 loop 로 라우팅.
provider 가 dartlab (휴리스틱) 이면 기존 `WorkbenchLoop` 유지.

순서:
    BRIEF → WORK → CRITIQUE → COMPOSE → GATE → HARVEST
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from dartlab.ai.contracts import TraceEvent
from dartlab.ai.memory import DecisionMemo, remember
from dartlab.ai.providers import create_provider
from dartlab.ai.providers.base import LLMProvider
from dartlab.ai.settings.types import LLMConfig

from .brief import runBrief
from .compose import runCompose
from .critique import runCritique
from .gate import runGate
from .harvest import runHarvest
from .scratchpad import Scratchpad
from .state import WorkbenchState
from .work import runWork

PASS_NODES: tuple[str, ...] = ("brief", "work", "critique", "compose", "gate", "harvest")


class PassLoop:
    """LLM-driven 5-pass workbench."""

    nodes = PASS_NODES

    def __init__(self, *, provider: LLMProvider | None = None, providerConfig: LLMConfig | None = None) -> None:
        self.provider = provider or create_provider(providerConfig or LLMConfig(provider="anthropic"))

    def stream(self, question: str, **kwargs: Any) -> Iterator[TraceEvent]:
        state = WorkbenchState(
            question=str(question or "").strip(),
            threadId=str(kwargs.get("threadId") or ""),
            messages=list(kwargs.get("history") or kwargs.get("messages") or []),
        )
        scratchpad = Scratchpad(state.runId)
        activity = 0

        # BRIEF
        for ev in runBrief(state, self.provider):
            scratchpad.append("brief", ev.data)
            activity += 1
            yield ev

        # WORK
        for ev in runWork(state, self.provider):
            scratchpad.append("work", ev.data)
            activity += 1
            yield ev

        # CRITIQUE
        for ev in runCritique(state, self.provider):
            scratchpad.append("critique", ev.data)
            activity += 1
            yield ev

        # COMPOSE
        for ev in runCompose(state, self.provider):
            scratchpad.append("compose", ev.data)
            activity += 1
            yield ev

        # GATE
        for ev in runGate(state):
            scratchpad.append("gate", ev.data)
            activity += 1
            yield ev

        # HARVEST — skill 통계 누적 + 선택적 propose_skill
        for ev in runHarvest(state, self.provider):
            scratchpad.append("harvest", ev.data)
            activity += 1
            yield ev

        # Stream final answer + done
        answer = str(state.profile.get("answer") or "")
        if state.failure:
            state.status = "failed"
            yield TraceEvent("chunk", {"text": answer})
            yield TraceEvent(
                "done",
                {
                    "refs": [ref.to_dict() for ref in state.refs],
                    "artifacts": [],
                    "verification": {
                        "ok": False,
                        "issues": state.verification.get("issues") or [],
                        "refId": "verify:gate",
                    },
                    "responseMeta": {
                        "finalEvent": "unable",
                        "responseStatus": "failed",
                        "failureReason": state.failure,
                        "activityCount": activity,
                        "scratchpad": scratchpad.ref(),
                    },
                },
            )
            return

        state.status = "done"
        try:
            remember(
                DecisionMemo(
                    question=state.question,
                    answer=answer,
                    refs=[ref.id for ref in state.refs],
                    verdict="ok",
                )
            )
        except Exception:  # noqa: BLE001 — 메모리 실패가 답변 흐름을 막지 않게
            pass
        for chunk in _chunks(answer):
            yield TraceEvent("chunk", {"text": chunk})
        yield TraceEvent(
            "done",
            {
                "refs": [ref.to_dict() for ref in state.refs],
                "artifacts": [],
                "verification": {"ok": True, "refId": "verify:gate"},
                "responseMeta": {
                    "finalEvent": "answer",
                    "responseStatus": "ok",
                    "refCount": len(state.refs),
                    "activityCount": activity,
                    "scratchpad": scratchpad.ref(),
                },
            },
        )


def _chunks(text: str, *, size: int = 240) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


__all__ = ["PassLoop", "PASS_NODES"]
