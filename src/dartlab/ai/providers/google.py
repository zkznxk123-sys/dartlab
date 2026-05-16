"""Google provider adapter (Gemini via google-genai SDK)."""

from __future__ import annotations

import os
from typing import Any, Iterator

from dartlab.ai.providers.base import BaseProvider, LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec


class GoogleProvider(BaseProvider):
    """Google Gemini provider adapter — google-genai SDK 래핑 + native tool."""

    name = "google"
    defaultModel = "gemini-2.0-flash-exp"

    def _client(self) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai SDK 가 설치되지 않았다") from exc
        apiKey = self.config.apiKey or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not apiKey:
            raise RuntimeError("GOOGLE_API_KEY 가 없다")
        return genai.Client(apiKey=apiKey)

    def checkAvailable(self) -> bool:
        """GOOGLE_API_KEY/GEMINI_API_KEY + google-genai SDK 동시 보유 여부."""
        if not (self.config.apiKey or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
            return False
        try:
            from google import genai  # noqa: F401
        except ImportError:
            return False
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
        """ToolSpec → Gemini function_declarations 형식 ($schema/additionalProperties 제거)."""
        return {
            "name": spec.name,
            "description": spec.description,
            "parameters": _stripJsonSchema(spec.inputSchema),
        }

    def complete(
        self,
        messages: list[Msg],
        tools: list[ToolSpec],
        *,
        stream: bool = True,
    ) -> Iterator[LLMEvent]:
        """messages + tools → google-genai API → LLMEvent stream (text/tool_use/stop)."""
        client = self._client()
        contents = _toGenaiContents(messages)
        cfg: dict[str, Any] = {}
        if self.config.temperature is not None:
            cfg["temperature"] = self.config.temperature
        if self.config.maxTokens is not None:
            cfg["max_output_tokens"] = self.config.maxTokens
        if tools:
            cfg["tools"] = [{"function_declarations": [self.toolSchema(t) for t in tools]}]

        kwargs: dict[str, Any] = {"model": self.resolvedModel, "contents": contents}
        if cfg:
            kwargs["config"] = cfg

        if not stream:
            resp = client.models.generate_content(**kwargs)
            yield from _eventsFromGenaiResponse(resp)
            return

        for chunk in client.models.generate_content_stream(**kwargs):
            yield from _eventsFromGenaiResponse(chunk, terminal=False)
        yield LLMEvent("stop", {"reason": "stop", "usage": {}})


def _toGenaiContents(messages: list[Msg]) -> list[dict[str, Any]]:
    """Translate neutral schema → google-genai contents (function_call/response)."""

    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            continue
        if role == "tool":
            parts: list[dict[str, Any]] = []
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    parts.append(
                        {
                            "function_response": {
                                "name": str(block.get("tool_use_id") or ""),
                                "response": _wrapResponse(block.get("content")),
                            }
                        }
                    )
            else:
                parts.append({"text": str(content or "")})
            out.append({"role": "user", "parts": parts})
            continue
        if role == "assistant":
            parts: list[dict[str, Any]] = []
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        parts.append({"text": str(block.get("text", ""))})
                    elif block.get("type") == "tool_use":
                        parts.append(
                            {
                                "function_call": {
                                    "name": str(block.get("name") or ""),
                                    "args": dict(block.get("input") or {}),
                                }
                            }
                        )
            else:
                parts.append({"text": str(content or "")})
            out.append({"role": "model", "parts": parts})
            continue
        # user
        if isinstance(content, str):
            out.append({"role": "user", "parts": [{"text": content}]})
        elif isinstance(content, list):
            text_parts = [
                {"text": str(b.get("text", ""))} for b in content if isinstance(b, dict) and b.get("type") == "text"
            ]
            out.append({"role": "user", "parts": text_parts or [{"text": ""}]})
        else:
            out.append({"role": "user", "parts": [{"text": str(content)}]})
    return out


def _wrapResponse(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"result": str(value or "")}


def _eventsFromGenaiResponse(resp: Any, *, terminal: bool = True) -> Iterator[LLMEvent]:
    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "text", None):
                yield LLMEvent("text", {"delta": part.text})
            fc = getattr(part, "function_call", None)
            if fc is not None:
                yield LLMEvent(
                    "tool_use",
                    {
                        "id": getattr(fc, "id", "") or fc.name,
                        "name": fc.name,
                        "input": dict(getattr(fc, "args", {}) or {}),
                    },
                )
    if terminal:
        yield LLMEvent("stop", {"reason": "stop", "usage": {}})


def _stripJsonSchema(schema: dict[str, Any]) -> dict[str, Any]:
    out = dict(schema)
    out.pop("$schema", None)
    out.pop("additionalProperties", None)
    if "properties" in out and isinstance(out["properties"], dict):
        out["properties"] = {k: _stripJsonSchema(v) for k, v in out["properties"].items()}
    return out


__all__ = ["GoogleProvider"]
