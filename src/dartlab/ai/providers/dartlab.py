"""DartLab built-in provider — research-graph compatible adapter.

기존 server/cli/setup 등이 의존하는 `provider="dartlab"` 호출 호환층.
LLM 직접 호출 없이 작업대 휴리스틱 경로 (P1 까지) 를 위한 호환 어댑터다.
P1 완료 시점에 작업대가 직접 다른 어댑터로 라우팅되면 본 어댑터는
backward-compat 만 유지한다.
"""

from __future__ import annotations

from typing import Any, Iterator

from dartlab.ai.providers.base import BaseProvider, LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec


class DartLabProvider(BaseProvider):
    """DartLabProvider — TODO 한국어 클래스 설명."""

    name = "dartlab"
    defaultModel = "dartlab-research-graph"

    def checkAvailable(self) -> bool:
        """checkAvailable — TODO 한국어 동작 설명."""
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
        """toolSchema — TODO 한국어 동작 설명."""
        return {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.inputSchema,
        }

    def complete(
        self,
        messages: list[Msg],
        tools: list[ToolSpec],
        *,
        stream: bool = True,
    ) -> Iterator[LLMEvent]:
        """complete — TODO 한국어 동작 설명."""
        yield LLMEvent(
            "stop",
            {"reason": "dartlab_research_graph", "usage": {}},
        )


__all__ = ["DartLabProvider"]
