"""Compatibility shim for the retired legacy prompt builder.

The official prompt and event contract are owned by ``dartlab.ai.kernel``.
This module only keeps stale imports working.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.runtime.workspace_agent import buildWorkspaceAgentSystemPrompt


def buildSystemPromptParts(
    _config: Any,
    *,
    question: str | None = None,
    stockCode: str | None = None,
    corpName: str | None = None,
    templateText: str | None = None,
    **_kwargs: Any,
) -> tuple[str, str]:
    prompt = buildWorkspaceAgentSystemPrompt(question=question or "", stockCode=stockCode, corpName=corpName)
    if templateText:
        prompt += "\n\n요청 템플릿:\n" + templateText
    return prompt, ""


def buildSelfDescription() -> str:
    return "DartLab Ask Workbench Kernel: Plan -> One Tool -> Observe -> Decide -> Verify."
