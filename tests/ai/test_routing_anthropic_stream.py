"""routeModelByComplexity + AnthropicProvider.generateStream 단위 — 마스터 플랜 v2 트랙 6 PR-L3.

외부 호출 0 — mock SDK 응답 + module helper 직접.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dartlab.ai.providers import ProviderTurn, StreamChunk, routeModelByComplexity

pytestmark = pytest.mark.unit


# ────────────────────────── routeModelByComplexity ──────────────────────────


def test_routing_cheap_for_short_lookup() -> None:
    """짧고 cheap 키워드 → cheap tier."""
    out = routeModelByComplexity("ROE 알려줘", "anthropic")
    assert out == "claude-haiku-4-5"


def test_routing_deep_for_dcf_keyword() -> None:
    """DCF 키워드 → deep tier (정밀 분석)."""
    out = routeModelByComplexity("삼성전자 DCF 평가해줘", "anthropic")
    assert out == "claude-opus-4-7"


def test_routing_standard_for_generic_question() -> None:
    """일반 길이 + 일반 키워드 → standard tier."""
    out = routeModelByComplexity("삼성전자 사업 어떻게 돼?", "anthropic")
    assert out == "claude-sonnet-4-5-20250929"


def test_routing_deep_for_long_question() -> None:
    """200 자+ → deep tier."""
    long_q = "삼성전자 " * 60
    out = routeModelByComplexity(long_q, "anthropic")
    assert out == "claude-opus-4-7"


def test_routing_explicit_tier_override() -> None:
    """configuredTier 명시 시 그 값 사용."""
    out = routeModelByComplexity("ROE", "anthropic", configuredTier="deep")
    assert out == "claude-opus-4-7"


def test_routing_env_tier_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """DARTLAB_AI_TIER 환경변수 강제."""
    monkeypatch.setenv("DARTLAB_AI_TIER", "cheap")
    out = routeModelByComplexity("삼성전자 DCF 평가", "anthropic")
    assert out == "claude-haiku-4-5"


def test_routing_openai_provider() -> None:
    out = routeModelByComplexity("ROE", "openai")
    assert out == "gpt-4o-mini"


def test_routing_gemini_provider() -> None:
    out = routeModelByComplexity("DCF 평가", "gemini")
    assert out == "gemini-2.5-pro"


def test_routing_unknown_provider_returns_none() -> None:
    assert routeModelByComplexity("ROE", "unknown") is None


def test_routing_empty_question() -> None:
    out = routeModelByComplexity("", "anthropic")
    assert out == "claude-sonnet-4-5-20250929"


# ────────────────────────── AnthropicProvider.generateStream ──────────────────────────


class _MockAnthropic:
    """AnthropicProvider 가 instantiate 가능하도록 BaseProvider 추상 메서드 채운 subclass."""


def _makeProvider(monkeypatch: pytest.MonkeyPatch, events: list):
    """AnthropicProvider 인스턴스 + complete 가 mock events yield 하도록 monkeypatch."""
    from dartlab.ai.providers.anthropic import AnthropicProvider
    from dartlab.ai.providers.base import LLMEvent

    class _ConcreteAnthropic(AnthropicProvider):
        def stream(self, messages):  # noqa: ARG002
            return iter([])

        @property
        def defaultModel(self) -> str:  # type: ignore[override]
            return "claude-sonnet-4-5-20250929"

    cfg = SimpleNamespace(
        model="claude-sonnet-4-5-20250929",
        apiKey="dummy",
        baseUrl=None,
        temperature=None,
        maxTokens=4096,
        provider="anthropic",
    )
    provider = _ConcreteAnthropic(cfg)

    def _mockComplete(self, messages, tools, *, stream=True):  # noqa: ARG001
        yield from (LLMEvent(kind, data) for kind, data in events)

    monkeypatch.setattr(_ConcreteAnthropic, "complete", _mockComplete, raising=True)
    return provider


def test_generateStream_text_delta_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """text delta 만 → StreamChunk(text=...) 즉시 + final ProviderTurn."""
    events = [
        ("text", {"delta": "안녕"}),
        ("text", {"delta": "하세요"}),
        ("stop", {"reason": "end_turn", "usage": {"input_tokens": 10, "output_tokens": 5}}),
    ]
    provider = _makeProvider(monkeypatch, events)
    chunks = list(provider.generateStream([{"role": "user", "content": "안녕"}], []))
    assert chunks[0] == StreamChunk(text="안녕")
    assert chunks[1] == StreamChunk(text="하세요")
    assert chunks[-1].final is True
    assert chunks[-1].turn.content == "안녕하세요"
    assert chunks[-1].turn.toolCalls == []


def test_generateStream_tool_use(monkeypatch: pytest.MonkeyPatch) -> None:
    """tool_use event → final ProviderTurn.toolCalls 에 누적."""
    events = [
        ("text", {"delta": "분석 중"}),
        ("tool_use", {"id": "t1", "name": "DCFValuation", "input": {"stockCode": "005930"}}),
        ("stop", {"reason": "tool_use", "usage": {"input_tokens": 50, "output_tokens": 20}}),
    ]
    provider = _makeProvider(monkeypatch, events)
    chunks = list(provider.generateStream([{"role": "user", "content": "DCF"}], []))
    final = chunks[-1]
    assert final.final is True
    assert len(final.turn.toolCalls) == 1
    assert final.turn.toolCalls[0].name == "DCFValuation"
    assert final.turn.toolCalls[0].args == {"stockCode": "005930"}


def test_generateStream_openai_tool_format_converted(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenAI 양식 tool dict 인자 → Anthropic 양식 변환 후 complete 에 전달."""
    captured: dict = {}

    from dartlab.ai.providers.anthropic import AnthropicProvider
    from dartlab.ai.providers.base import LLMEvent

    class _ConcreteAnthropic(AnthropicProvider):
        def stream(self, messages):  # noqa: ARG002
            return iter([])

        @property
        def defaultModel(self) -> str:  # type: ignore[override]
            return "claude-sonnet-4-5-20250929"

    cfg = SimpleNamespace(
        model="claude-sonnet-4-5-20250929",
        apiKey="dummy",
        baseUrl=None,
        temperature=None,
        maxTokens=4096,
        provider="anthropic",
    )
    provider = _ConcreteAnthropic(cfg)

    def _mockComplete(self, messages, tools, *, stream=True):  # noqa: ARG001
        captured["tools"] = tools
        yield LLMEvent("stop", {"reason": "end_turn", "usage": {}})

    monkeypatch.setattr(_ConcreteAnthropic, "complete", _mockComplete, raising=True)
    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "DCFValuation",
                "description": "DCF",
                "parameters": {"type": "object", "properties": {"stockCode": {"type": "string"}}},
            },
        }
    ]
    list(provider.generateStream([{"role": "user", "content": "x"}], openai_tools))
    assert len(captured["tools"]) == 1
    spec = captured["tools"][0]
    assert spec.name == "DCFValuation"
    assert spec.inputSchema == {"type": "object", "properties": {"stockCode": {"type": "string"}}}


def test_generateStream_empty_text_delta_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        ("text", {"delta": ""}),
        ("text", {"delta": "ok"}),
        ("stop", {"reason": "end_turn", "usage": {}}),
    ]
    provider = _makeProvider(monkeypatch, events)
    chunks = list(provider.generateStream([], []))
    text_chunks = [c for c in chunks if not c.final]
    assert len(text_chunks) == 1
    assert text_chunks[0].text == "ok"
