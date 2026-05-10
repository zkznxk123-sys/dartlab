"""Workbench state for ask runs (5 패스 작업대)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from dartlab.ai.contracts import Ref


@dataclass
class WorkbenchState:
    """WorkbenchState — TODO 한국어 클래스 설명."""

    question: str
    threadId: str = ""
    runId: str = field(default_factory=lambda: uuid4().hex[:12])

    # BRIEF
    intent: str = "research"
    profile: dict[str, Any] = field(default_factory=dict)
    selectedSkillRefs: list[Ref] = field(default_factory=list)
    apiRefs: list[Ref] = field(default_factory=list)
    requiredEvidence: list[str] = field(default_factory=list)
    plan: list[dict[str, Any]] = field(default_factory=list)
    recall: list[dict[str, Any]] = field(default_factory=list)

    # WORK
    toolCalls: list[dict[str, Any]] = field(default_factory=list)
    refs: list[Ref] = field(default_factory=list)

    # CRITIQUE
    critiques: list[dict[str, Any]] = field(default_factory=list)

    # COMPOSE
    answerText: str = ""
    claims: list[dict[str, Any]] = field(default_factory=list)

    # GATE
    verification: dict[str, Any] = field(default_factory=dict)
    gateBlocked: bool = False
    gateIssues: list[str] = field(default_factory=list)

    # HARVEST
    harvestProposals: list[dict[str, Any]] = field(default_factory=list)

    # control
    iteration: int = 0
    status: str = "running"
    failure: str | None = None
    currentPass: str = "init"

    # internal — recipe 한 번만 전개 (BRIEF retry 시 재전개 방지). 명시적 boolean.
    recipeExpanded: bool = False

    def public(self, *, currentNode: str) -> dict[str, Any]:
        """public — TODO 한국어 동작 설명."""
        return {
            "threadId": self.threadId,
            "runId": self.runId,
            "currentNode": currentNode,
            "currentPass": self.currentPass,
            "intent": self.intent,
            "profile": self.profile,
            "selectedSkillRefs": [ref.id for ref in self.selectedSkillRefs],
            "apiRefs": [ref.id for ref in self.apiRefs],
            "toolCalls": len(self.toolCalls),
            "refs": [ref.id for ref in self.refs],
            "iteration": self.iteration,
            "status": self.status,
            "failure": self.failure,
            "gateBlocked": self.gateBlocked,
        }
