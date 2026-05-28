"""Anthropic ``cache_control`` 인프라 단위 테스트 — PR-O3.

마스터 플랜 트랙 2 PR-O3. 환경변수 ``DARTLAB_ANTHROPIC_CACHE=1`` 토글 ON/OFF +
system block + 마지막 tool spec 마커 + usage dict cache_creation/read tokens
노출 결정론 검증. anthropic SDK 호출은 없음 — kwargs builder 단독 검증.
"""

from __future__ import annotations

from typing import Any

import pytest

from dartlab.ai.providers import ProviderConfig
from dartlab.ai.providers.anthropic import (
    AnthropicProvider,
    _systemBlocksWithCache,
    _usageDict,
)
from dartlab.ai.tools.types import ToolSpec

pytestmark = pytest.mark.unit


def _toolSpec(name: str) -> ToolSpec:
    return ToolSpec(
        name=name,
        description=f"{name} desc",
        inputSchema={"type": "object", "properties": {}},
    )


class _ConcreteAnthropic(AnthropicProvider):
    """BaseProvider abstract method (stream/complete legacy 시그니처) 채운 테스트 stub.

    AnthropicProvider 의 cache_control 동작 검증 전용. 실제 catalog.createProvider 도
    동일 ABC 우회 (instantiate 직전 abstract 미구현 회피). 본 stub 가 검증 단위.
    """

    def stream(self, messages):  # type: ignore[override]
        raise NotImplementedError

    @property
    def defaultModel(self) -> str:  # type: ignore[override]
        return "claude-sonnet-4-5-20250929"


def test_supportsCacheControl_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경변수 unset → 캐시 OFF."""
    monkeypatch.delenv("DARTLAB_ANTHROPIC_CACHE", raising=False)
    p = _ConcreteAnthropic(ProviderConfig(provider="anthropic", apiKey="x"))
    assert p.supportsCacheControl is False


def test_supportsCacheControl_truthy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """1 / true / yes / on 모두 ON."""
    p = _ConcreteAnthropic(ProviderConfig(provider="anthropic", apiKey="x"))
    for v in ("1", "true", "TRUE", "yes", "on"):
        monkeypatch.setenv("DARTLAB_ANTHROPIC_CACHE", v)
        assert p.supportsCacheControl is True


def test_supportsCacheControl_falsy_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """0 / false / off → OFF."""
    p = _ConcreteAnthropic(ProviderConfig(provider="anthropic", apiKey="x"))
    for v in ("0", "false", "off", ""):
        monkeypatch.setenv("DARTLAB_ANTHROPIC_CACHE", v)
        assert p.supportsCacheControl is False


def test_systemBlocksWithCache_single_text_block_with_marker() -> None:
    """system 문자열 → cache_control ephemeral 부착 single text block."""
    blocks = _systemBlocksWithCache("you are a helpful assistant")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "text"
    assert blocks[0]["text"] == "you are a helpful assistant"
    assert blocks[0]["cache_control"] == {"type": "ephemeral"}


def test_usageDict_exposes_cache_tokens() -> None:
    """usage SDK 객체 → cache_creation/read tokens 동행 노출."""

    class _U:
        input_tokens = 100
        output_tokens = 50
        cache_creation_input_tokens = 200
        cache_read_input_tokens = 800

    d = _usageDict(_U())
    assert d["input_tokens"] == 100
    assert d["output_tokens"] == 50
    assert d["cache_creation_input_tokens"] == 200
    assert d["cache_read_input_tokens"] == 800


def test_usageDict_missing_cache_fields_default_zero() -> None:
    """cache_* attribute 없는 옛 usage 객체 → 0 fallback (None safe)."""

    class _OldU:
        input_tokens = 100
        output_tokens = 50

    d = _usageDict(_OldU())
    assert d["cache_creation_input_tokens"] == 0
    assert d["cache_read_input_tokens"] == 0


def test_usageDict_none_input() -> None:
    """usage None → empty dict."""
    assert _usageDict(None) == {}


def test_cache_off_passes_string_system(monkeypatch: pytest.MonkeyPatch) -> None:
    """캐시 OFF → kwargs['system'] 은 plain string (이전 동작 회귀 가드)."""
    monkeypatch.delenv("DARTLAB_ANTHROPIC_CACHE", raising=False)
    captured: dict[str, Any] = {}

    class _FakeMessages:
        def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)

            class _Resp:
                content = []
                stop_reason = "end_turn"
                usage = None

            return _Resp()

    class _FakeClient:
        messages = _FakeMessages()

    p = _ConcreteAnthropic(ProviderConfig(provider="anthropic", apiKey="x", model="claude-sonnet-4-5-20250929"))
    p._client = lambda: _FakeClient()  # type: ignore[method-assign]

    messages = [
        {"role": "system", "content": "you are helpful"},
        {"role": "user", "content": "hi"},
    ]
    list(p.complete(messages, tools=[_toolSpec("A"), _toolSpec("B")], stream=False))
    assert isinstance(captured["system"], str)
    assert captured["system"] == "you are helpful"
    # tools 마지막에 cache_control 없음
    tools_kw = captured.get("tools") or []
    assert all("cache_control" not in t for t in tools_kw)


def test_cache_on_marks_system_and_last_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    """캐시 ON → system 은 block list + 마지막 tool 만 cache_control 부착."""
    monkeypatch.setenv("DARTLAB_ANTHROPIC_CACHE", "1")
    captured: dict[str, Any] = {}

    class _FakeMessages:
        def create(self, **kwargs: Any) -> Any:
            captured.update(kwargs)

            class _Resp:
                content = []
                stop_reason = "end_turn"

                class usage:
                    input_tokens = 10
                    output_tokens = 5
                    cache_creation_input_tokens = 100
                    cache_read_input_tokens = 0

            return _Resp()

    class _FakeClient:
        messages = _FakeMessages()

    p = _ConcreteAnthropic(ProviderConfig(provider="anthropic", apiKey="x", model="claude-sonnet-4-5-20250929"))
    p._client = lambda: _FakeClient()  # type: ignore[method-assign]

    messages = [
        {"role": "system", "content": "you are helpful"},
        {"role": "user", "content": "hi"},
    ]
    events = list(p.complete(messages, tools=[_toolSpec("A"), _toolSpec("B"), _toolSpec("C")], stream=False))

    # system 은 block list with cache_control
    sys = captured["system"]
    assert isinstance(sys, list)
    assert sys[0]["cache_control"] == {"type": "ephemeral"}

    # tools — 마지막 1 개만 cache_control. 4-block hard limit 준수 = 2 block 사용.
    tools_kw = captured["tools"]
    assert len(tools_kw) == 3
    assert "cache_control" not in tools_kw[0]
    assert "cache_control" not in tools_kw[1]
    assert tools_kw[2]["cache_control"] == {"type": "ephemeral"}

    # stop event usage 에 cache token 동행
    stop_ev = next(e for e in events if e.kind == "stop")
    assert stop_ev.data["usage"]["cache_creation_input_tokens"] == 100
    assert stop_ev.data["usage"]["cache_read_input_tokens"] == 0
