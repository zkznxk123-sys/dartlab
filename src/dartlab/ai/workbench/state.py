"""Workbench state for ask runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from dartlab.ai.contracts import Ref


@dataclass
class WorkbenchState:
    question: str
    threadId: str = ""
    runId: str = field(default_factory=lambda: uuid4().hex[:12])
    messages: list[dict[str, Any]] = field(default_factory=list)
    intent: str = "research"
    profile: dict[str, Any] = field(default_factory=dict)
    plan: list[dict[str, Any]] = field(default_factory=list)
    selectedSkillRefs: list[Ref] = field(default_factory=list)
    apiRefs: list[Ref] = field(default_factory=list)
    toolCalls: list[dict[str, Any]] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    iteration: int = 0
    status: str = "running"
    failure: str | None = None

    def public(self, *, currentNode: str) -> dict[str, Any]:
        return {
            "threadId": self.threadId,
            "runId": self.runId,
            "currentNode": currentNode,
            "intent": self.intent,
            "profile": self.profile,
            "selectedSkillRefs": [ref.id for ref in self.selectedSkillRefs],
            "apiRefs": [ref.id for ref in self.apiRefs],
            "toolCalls": len(self.toolCalls),
            "refs": [ref.id for ref in self.refs],
            "iteration": self.iteration,
            "status": self.status,
            "failure": self.failure,
        }
