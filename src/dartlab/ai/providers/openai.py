"""OpenAI provider adapter (chat completions)."""

from __future__ import annotations

import json
import os
from typing import Any, Iterator

from dartlab.ai.providers.base import BaseProvider, LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec


class OpenAIProvider(BaseProvider):
    """OpenAI provider adapter — openai SDK 래핑 + native tool calling."""

    name = "openai"
    defaultModel = "gpt-4o"

    def _client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai SDK 가 설치되지 않았다") from exc
        apiKey = self.config.apiKey or os.getenv("OPENAI_API_KEY")
        if not apiKey:
            raise RuntimeError("OPENAI_API_KEY 가 없다")
        return OpenAI(apiKey=apiKey, baseUrl=self.config.baseUrl or None)

    def checkAvailable(self) -> bool:
        """OPENAI_API_KEY + openai SDK 동시 보유 여부."""
        if not (self.config.apiKey or os.getenv("OPENAI_API_KEY")):
            return False
        try:
            from openai import OpenAI  # noqa: F401
        except ImportError:
            return False
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
        """ToolSpec → OpenAI chat.completions tools 형식 (type=function 래핑)."""
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.inputSchema,
            },
        }

    def complete(
        self,
        messages: list[Msg],
        tools: list[ToolSpec],
        *,
        stream: bool = True,
    ) -> Iterator[LLMEvent]:
        """messages + tools → OpenAI chat.completions → LLMEvent stream."""
        client = self._client()
        kwargs: dict[str, Any] = {
            "model": self.resolvedModel,
            "messages": _toOpenAIMessages(messages),
        }
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if self.config.maxTokens is not None:
            kwargs["max_tokens"] = self.config.maxTokens
        if tools:
            kwargs["tools"] = [self.toolSchema(t) for t in tools]

        if not stream:
            resp = client.chat.completions.create(**kwargs)
            yield from _eventsFromChatCompletion(resp)
            return

        kwargs["stream"] = True
        tool_buf: dict[int, dict[str, str]] = {}
        finish: str = ""
        for chunk in client.chat.completions.create(**kwargs):
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = choice.delta
            if getattr(delta, "content", None):
                yield LLMEvent("text", {"delta": delta.content})
            for tc in getattr(delta, "tool_calls", []) or []:
                idx = tc.index
                buf = tool_buf.setdefault(idx, {"id": "", "name": "", "args": ""})
                if tc.id:
                    buf["id"] = tc.id
                if tc.function and tc.function.name:
                    buf["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    buf["args"] += tc.function.arguments
            if choice.finish_reason:
                finish = choice.finish_reason
        for buf in tool_buf.values():
            try:
                parsed = json.loads(buf["args"]) if buf["args"] else {}
            except json.JSONDecodeError:
                parsed = {}
            yield LLMEvent(
                "tool_use",
                {"id": buf["id"], "name": buf["name"], "input": parsed},
            )
        yield LLMEvent("stop", {"reason": finish or "stop", "usage": {}})


def _toOpenAIMessages(messages: list[Msg]) -> list[dict[str, Any]]:
    """Translate neutral schema → OpenAI chat completions format."""

    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role in ("system", "user"):
            if isinstance(content, list):
                text_parts = [
                    str(b.get("text", "")) for b in content if isinstance(b, dict) and b.get("type") == "text"
                ]
                out.append({"role": role, "content": "\n".join(text_parts)})
            else:
                out.append({"role": role, "content": str(content or "")})
            continue
        if role == "assistant":
            text_parts: list[str] = []
            toolCalls: list[dict[str, Any]] = []
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text_parts.append(str(block.get("text", "")))
                    elif block.get("type") == "tool_use":
                        toolCalls.append(
                            {
                                "id": str(block.get("id") or ""),
                                "type": "function",
                                "function": {
                                    "name": str(block.get("name") or ""),
                                    "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False),
                                },
                            }
                        )
            else:
                text_parts.append(str(content or ""))
            entry: dict[str, Any] = {"role": "assistant"}
            entry["content"] = "\n".join(text_parts) if text_parts else None
            if toolCalls:
                entry["tool_calls"] = toolCalls
            out.append(entry)
            continue
        if role == "tool":
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_result":
                        continue
                    raw = block.get("content")
                    out.append(
                        {
                            "role": "tool",
                            "tool_call_id": str(block.get("tool_use_id") or ""),
                            "content": _serializeToolContent(raw),
                        }
                    )
            else:
                out.append({"role": "tool", "tool_call_id": "", "content": str(content or "")})
            continue
        out.append({"role": role or "user", "content": str(content or "")})
    return out


def _serializeToolContent(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(value)


def _eventsFromChatCompletion(resp: Any) -> Iterator[LLMEvent]:
    choice = resp.choices[0]
    msg = choice.message
    if getattr(msg, "content", None):
        yield LLMEvent("text", {"delta": msg.content})
    for tc in getattr(msg, "tool_calls", []) or []:
        try:
            parsed = json.loads(tc.function.arguments) if tc.function.arguments else {}
        except json.JSONDecodeError:
            parsed = {}
        yield LLMEvent(
            "tool_use",
            {"id": tc.id, "name": tc.function.name, "input": parsed},
        )
    yield LLMEvent(
        "stop", {"reason": choice.finish_reason or "stop", "usage": _usageDict(getattr(resp, "usage", None))}
    )


def _usageDict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "prompt_tokens", 0),
        "output_tokens": getattr(usage, "completion_tokens", 0),
    }


__all__ = ["OpenAIProvider"]
