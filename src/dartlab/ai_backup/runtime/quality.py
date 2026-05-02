"""Compatibility shim for the retired text-first quality gate.

Workspace-native verification now lives in ``runtime.workspace_verify`` and is
run through ``finalize_answer``.  This module no longer owns answer quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityIssue:
    code: str
    detail: str = ""


@dataclass
class QualityResult:
    ok: bool = True
    issues: list[QualityIssue] = field(default_factory=list)
    rewriteInstruction: str | None = None

    def toDict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "issues": [issue.__dict__ for issue in self.issues],
            "rewriteInstruction": self.rewriteInstruction,
        }


def evaluateFinalAnswer(*_args: Any, **_kwargs: Any) -> QualityResult:
    """Return a neutral result for stale imports.

    The active verifier is request-local and requires an ``AgentSession``.
    Call ``workspace_verify.finalizeAnswer`` through the workspace tools.
    """
    return QualityResult(ok=True, issues=[])
