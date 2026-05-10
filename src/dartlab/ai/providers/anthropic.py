"""Anthropic provider adapter (Claude)."""

from __future__ import annotations

import os
from typing import Any, Iterator

from dartlab.ai.providers.base import BaseProvider, LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    defaultModel = "claude-sonnet-4-5-20250929"

    def _client(self) -> Any:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic SDK 가 설치되지 않았다") from exc
        apiKey = self.config.apiKey or os.getenv("ANTHROPIC_API_KEY")
        if not apiKey:
            raise RuntimeError("ANTHROPIC_API_KEY 가 없다")
        return Anthropic(apiKey=apiKey, baseUrl=self.config.baseUrl or None)

    def checkAvailable(self) -> bool:
        if not (self.config.apiKey or os.getenv("ANTHROPIC_API_KEY")):
            return False
        try:
            from anthropic import Anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
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
        client = self._client()
        system, normalized = _splitSystem(messages)
        kwargs: dict[str, Any] = {
            "model": self.resolvedModel,
            "messages": normalized,
            "max_tokens": self.config.maxTokens or 4096,
        }
        if system:
            kwargs["system"] = system
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if tools:
            kwargs["tools"] = [self.toolSchema(t) for t in tools]

        if not stream:
            resp = client.messages.create(**kwargs)
            yield from _eventsFromAnthropicMessage(resp)
            return

        with client.messages.stream(**kwargs) as s:
            tool_buf: dict[int, dict[str, Any]] = {}
            for ev in s:
                t = getattr(ev, "type", "")
                if t == "content_block_start":
                    block = getattr(ev, "content_block", None)
                    if getattr(block, "type", "") == "tool_use":
                        tool_buf[ev.index] = {
                            "id": block.id,
                            "name": block.name,
                            "input": "",
                        }
                elif t == "content_block_delta":
                    delta = getattr(ev, "delta", None)
                    dt = getattr(delta, "type", "")
                    if dt == "text_delta":
                        yield LLMEvent("text", {"delta": delta.text})
                    elif dt == "input_json_delta":
                        if ev.index in tool_buf:
                            tool_buf[ev.index]["input"] += delta.partial_json
                elif t == "content_block_stop":
                    if ev.index in tool_buf:
                        import json

                        b = tool_buf.pop(ev.index)
                        try:
                            parsed = json.loads(b["input"]) if b["input"] else {}
                        except json.JSONDecodeError:
                            parsed = {}
                        yield LLMEvent(
                            "tool_use",
                            {"id": b["id"], "name": b["name"], "input": parsed},
                        )
                elif t == "message_stop":
                    final = s.get_final_message()
                    yield LLMEvent(
                        "stop",
                        {
                            "reason": getattr(final, "stop_reason", "") or "end_turn",
                            "usage": _usageDict(getattr(final, "usage", None)),
                        },
                    )


def _splitSystem(messages: list[Msg]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    rest: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            system_parts.append(str(m.get("content", "")))
            continue
        # Anthropic 은 tool_result 블록을 user 메시지에 담는다.
        anthropic_role = "user" if role == "tool" else role
        rest.append({"role": anthropic_role, "content": m["content"]})
    return ("\n\n".join(system_parts), rest)


def _eventsFromAnthropicMessage(resp: Any) -> Iterator[LLMEvent]:
    for block in getattr(resp, "content", []) or []:
        bt = getattr(block, "type", "")
        if bt == "text":
            yield LLMEvent("text", {"delta": block.text})
        elif bt == "tool_use":
            yield LLMEvent(
                "tool_use",
                {"id": block.id, "name": block.name, "input": dict(block.input or {})},
            )
    yield LLMEvent(
        "stop",
        {
            "reason": getattr(resp, "stop_reason", "") or "end_turn",
            "usage": _usageDict(getattr(resp, "usage", None)),
        },
    )


def _usageDict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }


__all__ = ["AnthropicProvider"]
