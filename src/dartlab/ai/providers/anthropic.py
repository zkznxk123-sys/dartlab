"""Anthropic provider adapter (Claude).

마스터 플랜 트랙 2 PR-O3 — Anthropic ``cache_control`` 도입. 환경변수
``DARTLAB_ANTHROPIC_CACHE=1`` ON 시 system prompt 블록 + 마지막 tool spec 에
``ephemeral`` 캐시 마커 부착 (4-block hard limit 중 2 block 사용 — 사용자
history 는 캐시 안 함 → 멀티턴 대화에서 가장 큰 블록인 system + tool spec 만
캐시 → 70%+ input_tokens 절약 목표). usage dict 에
``cache_creation_input_tokens`` / ``cache_read_input_tokens`` 노출.

OFF 가 기본 — provider 호환성 회귀 즉시 토글 가능.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

from dartlab.ai.providers.base import BaseProvider, LLMEvent, Msg
from dartlab.ai.tools.types import ToolSpec


def _cacheEnabled() -> bool:
    """환경변수 ``DARTLAB_ANTHROPIC_CACHE`` truthy → 캐시 ON."""
    return os.getenv("DARTLAB_ANTHROPIC_CACHE", "0").strip().lower() in {"1", "true", "yes", "on"}


class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) provider adapter — anthropic SDK 래핑 + native tool."""

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
        """ANTHROPIC_API_KEY + anthropic SDK 동시 보유 여부."""
        if not (self.config.apiKey or os.getenv("ANTHROPIC_API_KEY")):
            return False
        try:
            from anthropic import Anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def toolSchema(self, spec: ToolSpec) -> dict[str, Any]:
        """ToolSpec → Anthropic API native tool schema (name/description/input_schema)."""
        return {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.inputSchema,
        }

    @property
    def supportsCacheControl(self) -> bool:
        """캐시 활성 여부 — ``DARTLAB_ANTHROPIC_CACHE`` 환경변수 게이트.

        BaseProvider 의 ``@property supportsCacheControl`` 시그니처를 그대로 override.
        OFF 가 기본 — provider 호환성 회귀 즉시 토글.
        """
        return _cacheEnabled()

    def complete(
        self,
        messages: list[Msg],
        tools: list[ToolSpec],
        *,
        stream: bool = True,
    ) -> Iterator[LLMEvent]:
        """messages + tools → Anthropic API 호출 → LLMEvent stream (text/tool_call/stop).

        ``DARTLAB_ANTHROPIC_CACHE=1`` ON 시 system 블록 + 마지막 tool spec 에
        ``cache_control: {type: ephemeral}`` 마커 부착. 4-block hard limit 중 2
        block 만 사용 — 사용자 history 는 캐시 안 함.
        """
        client = self._client()
        system, normalized = _splitSystem(messages)
        cache_on = self.supportsCacheControl
        kwargs: dict[str, Any] = {
            "model": self.resolvedModel,
            "messages": normalized,
            "max_tokens": self.config.maxTokens or 4096,
        }
        if system:
            kwargs["system"] = _systemBlocksWithCache(system) if cache_on else system
        if self.config.temperature is not None:
            kwargs["temperature"] = self.config.temperature
        if tools:
            tool_dicts = [self.toolSchema(t) for t in tools]
            if cache_on and tool_dicts:
                # 마지막 tool 한 곳에만 ephemeral 마커 — 그 이전 도구는 자동으로 같은
                # 캐시 prefix 안에 들어감 (Anthropic 캐시 동작 — 마커 위치까지 누적 캐싱).
                tool_dicts[-1] = {**tool_dicts[-1], "cache_control": {"type": "ephemeral"}}
            kwargs["tools"] = tool_dicts

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

    def generateStream(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> Iterator[Any]:
        """ProviderConfig 진영의 streamProvider 호환 진입점 — Iterator[StreamChunk] 반환.

        마스터 플랜 v2 트랙 6 PR-L3 — agent.py 의 ``streamProvider(provider, messages, tools)``
        가 ``hasattr(provider, "generateStream")`` 으로 본 메서드를 우선 호출. text 델타는
        즉시 ``StreamChunk(text=...)``, 종료 시 ``StreamChunk(final=True, turn=ProviderTurn(...))``.

        ``complete()`` 가 이미 ``client.messages.stream`` 으로 진짜 SSE streaming 하니까
        그 LLMEvent 출력을 StreamChunk 로 어댑팅. tool spec 양식만 OpenAI → Anthropic 변환.
        """
        from dartlab.ai.providers import ProviderTurn, StreamChunk, ToolCall

        accumulated = ""
        tool_calls: list[ToolCall] = []
        norm_messages = list(messages)
        tool_specs = _openaiToolsToAnthropic(tools)

        for ev in self.complete(norm_messages, tool_specs, stream=True):
            if ev.kind == "text":
                delta = str(ev.data.get("delta", ""))
                if delta:
                    accumulated += delta
                    yield StreamChunk(text=delta)
            elif ev.kind == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=str(ev.data.get("id", "")),
                        name=str(ev.data.get("name", "")),
                        args=dict(ev.data.get("input") or {}),
                    )
                )
            elif ev.kind == "stop":
                raw = {"usage": dict(ev.data.get("usage") or {}), "reason": ev.data.get("reason", "")}
                yield StreamChunk(
                    final=True,
                    turn=ProviderTurn(content=accumulated, toolCalls=tool_calls, raw=raw),
                )


def _openaiToolsToAnthropic(tools: list[dict[str, Any]]) -> list[Any]:
    """OpenAI function-calling 양식 tool dict → Anthropic native ToolSpec-호환 객체.

    agent.py 의 ``_selectTools`` 는 OpenAI 양식 (``{type:"function", function:{name,description,parameters}}``)
    으로 emit. complete() 는 ToolSpec 객체 받음 → 본 helper 가 변환.
    """
    out: list[Any] = []
    for tool in tools or []:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(fn, dict):
            continue

        class _Spec:
            __slots__ = ("name", "description", "inputSchema")

            def __init__(self, name: str, description: str, inputSchema: dict[str, Any]) -> None:
                self.name = name
                self.description = description
                self.inputSchema = inputSchema

        out.append(
            _Spec(
                name=str(fn.get("name", "")),
                description=str(fn.get("description", "")),
                inputSchema=dict(fn.get("parameters") or {"type": "object", "properties": {}}),
            )
        )
    return out


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


def _systemBlocksWithCache(system: str) -> list[dict[str, Any]]:
    """system 문자열 → cache_control 부착 single text block.

    PR-O3 — 멀티턴 대화의 system prompt 는 변경 가능성 매우 낮은데 매 turn 모든 input
    토큰으로 청구되던 비효율 차단. ``ephemeral`` 5 분 TTL 캐시 → 5 분 안에 같은 system
    재호출 시 90% 할인 (Anthropic 가격표 기준).
    """
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def _usageDict(usage: Any) -> dict[str, Any]:
    """Anthropic usage → dict. PR-O3 cache_creation/read tokens 동행 노출.

    ``cache_creation_input_tokens`` = 캐시 *생성* (첫 호출), 일반 input 1.25x 가격.
    ``cache_read_input_tokens`` = 캐시 *적중* (재호출), 일반 input 0.1x 가격.
    KPI digest 가 두 값으로 hit rate (= cache_read / (cache_read + cache_create)) 계산.
    """
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
    }


__all__ = ["AnthropicProvider"]
