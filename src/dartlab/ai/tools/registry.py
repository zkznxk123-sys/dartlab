"""AI Tool Registry.

dartlab 공개 API 를 LLM tool calling 에 등록하는 프로세스 전역 저장소.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AITool:
    """등록된 tool 정의."""

    name: str
    description: str
    parameters: dict  # JSON Schema (properties/required/additionalProperties)
    handler: Callable[..., Any]


@dataclass
class AIToolRegistry:
    """프로세스 전역 tool 저장소."""

    tools: dict[str, AITool] = field(default_factory=dict)

    def register(self, tool: AITool) -> None:
        self.tools[tool.name] = tool

    def registerMany(self, tools: list[AITool]) -> None:
        for t in tools:
            self.register(t)

    def clear(self) -> None:
        self.tools.clear()

    def has(self, name: str) -> bool:
        return name in self.tools

    def list_names(self) -> list[str]:
        return list(self.tools.keys())

    def getOpenaiSchemas(self) -> list[dict]:
        """OpenAI function calling 형식 tool 리스트 반환.

        Claude Anthropic 네이티브는 providers/claude.py::_openai_tools_to_anthropic 가 자동 변환.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> Any:
        """Tool 핸들러 실행. 존재하지 않으면 ValueError."""
        tool = self.tools.get(name)
        if tool is None:
            raise ValueError(f"알 수 없는 tool: {name}. 등록된 tool: {list(self.tools.keys())}")
        return tool.handler(**arguments)


# ── 프로세스 전역 싱글턴 ────────────────────────────────────

_REGISTRY: AIToolRegistry | None = None


def getDefaultRegistry() -> AIToolRegistry:
    """프로세스 전역 기본 registry. bootstrapDefaultTools() 가 채운다."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = AIToolRegistry()
    return _REGISTRY


def resetDefaultRegistry() -> None:
    """테스트용 — registry 초기화."""
    global _REGISTRY
    _REGISTRY = None
