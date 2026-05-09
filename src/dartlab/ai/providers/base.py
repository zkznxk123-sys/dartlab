"""LLM provider 추상 베이스."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator

from dartlab.ai.types import LLMConfig, LLMResponse, ToolResponse


# 새 provider adapter 들 (anthropic / openai / google / dartlab) 이 stream API 로
# yield 하는 단위 이벤트. kind ∈ {text, tool_call, stop, error} 등. data 는 kind 별
# 의미 있는 dict (text→{"delta": str}, tool_call→{"id","name","arguments"}, stop→
# {"reason","usage"}). agent loop 가 kind 로 분기.
@dataclass(frozen=True)
class LLMEvent:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


# Provider 가 받는 message 의 type alias. role + content 를 가진 dict.
# tool 호출 중간 메시지는 tool_call_id, tool_calls 등 추가 키 가질 수 있어 Any.
Msg = dict[str, Any]


class RateLimitError(Exception):
    """429 rate limit 에러. fallback 체인에서 다음 프로바이더로 전환 트리거."""

    def __init__(self, provider: str, message: str = "", retryAfter: float | None = None):
        self.provider = provider
        self.retryAfter = retryAfter
        super().__init__(message or f"{provider}: rate limit 초과")


class BaseProvider(ABC):
    """모든 LLM provider의 추상 기반."""

    name: str = "base"

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> LLMResponse:
        """동기 completion 호출."""
        ...

    @abstractmethod
    def stream(self, messages: list[dict[str, str]]) -> Generator[str, None, None]:
        """스트리밍 completion (generator)."""
        ...

    @abstractmethod
    def check_available(self) -> bool:
        """provider 접근 가능 여부 확인."""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """provider 기본 모델명."""
        ...

    @property
    def resolved_model(self) -> str:
        """사용자 설정 모델 또는 기본 모델명 반환."""
        return self.config.model or self.default_model

    @property
    def supports_native_tools(self) -> bool:
        """이 provider가 네이티브 tool calling을 지원하는지."""
        return False

    @property
    def supports_cache_control(self) -> bool:
        """시스템 프롬프트 캐시 경계(cache_control)를 지원하는지."""
        return False

    def complete_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        tool_choice: str | None = None,
    ) -> ToolResponse:
        response = self.complete(messages)
        return ToolResponse(
            answer=response.answer,
            provider=response.provider,
            model=response.model,
            tool_calls=[],
            usage=response.usage,
            context_tables=response.context_tables,
        )

    def stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        tool_choice: str | None = None,
    ) -> Generator:
        resp = self.complete_with_tools(messages, tools, tool_choice=tool_choice)
        yield resp

    def format_tool_result(self, tool_call_id: str, result: str) -> dict:
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        }

    def format_assistant_tool_calls(
        self,
        answer: str | None,
        tool_calls: list,
    ) -> dict:
        import json

        msg: dict = {"role": "assistant", "content": answer}
        msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                },
            }
            for tc in tool_calls
        ]
        return msg


# 새 provider adapter 들이 사용하는 type alias. BaseProvider 와 동의어.
# 새 코드는 LLMProvider 를 type 힌트로 선호하고, BaseProvider 는 상속용 베이스로 유지.
LLMProvider = BaseProvider
