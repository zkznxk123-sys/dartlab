"""Provider 어댑터 — schema 변환과 LLMProvider Protocol 만족 검증.

실제 SDK 호출은 별도 통합 테스트에서 다룬다. 여기서는 LLM-agnostic 작업대를
받칠 어댑터 형식 계약만 본다.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.providers import LLMProvider, available_providers, create_provider
from dartlab.ai.providers.anthropic import AnthropicProvider
from dartlab.ai.providers.dartlab import DartLabProvider
from dartlab.ai.providers.google import GoogleProvider
from dartlab.ai.providers.ollama import OllamaProvider
from dartlab.ai.providers.openai import OpenAIProvider
from dartlab.ai.providers.xai import XAIProvider
from dartlab.ai.settings.types import LLMConfig
from dartlab.ai.tools.types import ToolSpec

SAMPLE_SPEC = ToolSpec(
    "run_python",
    "DartLab library 와 Polars 를 조합해 코드를 실행한다.",
    {
        "type": "object",
        "properties": {"code": {"type": "string"}, "runId": {"type": "string"}},
        "required": ["code"],
    },
)


@pytest.mark.parametrize(
    "provider_name,cls",
    [
        ("anthropic", AnthropicProvider),
        ("openai", OpenAIProvider),
        ("google", GoogleProvider),
        ("xai", XAIProvider),
        ("ollama", OllamaProvider),
        ("dartlab", DartLabProvider),
    ],
)
def test_create_provider_dispatches_to_adapter(provider_name: str, cls: type) -> None:
    provider = create_provider(LLMConfig(provider=provider_name))
    assert isinstance(provider, cls)
    assert isinstance(provider, LLMProvider)


def test_available_providers_lists_six() -> None:
    assert available_providers() == [
        "anthropic",
        "openai",
        "google",
        "xai",
        "ollama",
        "dartlab",
    ]


def test_resolved_model_uses_default_when_unset() -> None:
    assert create_provider(LLMConfig(provider="anthropic")).resolved_model == "claude-sonnet-4-5-20250929"
    assert create_provider(LLMConfig(provider="openai")).resolved_model == "gpt-4o"
    assert create_provider(LLMConfig(provider="google")).resolved_model == "gemini-2.0-flash-exp"
    assert create_provider(LLMConfig(provider="xai")).resolved_model == "grok-2-latest"
    assert create_provider(LLMConfig(provider="ollama")).resolved_model == "llama3.1"
    assert create_provider(LLMConfig(provider="dartlab")).resolved_model == "dartlab-research-graph"


def test_anthropic_tool_schema_uses_input_schema_key() -> None:
    schema = AnthropicProvider(LLMConfig()).toolSchema(SAMPLE_SPEC)
    assert schema == {
        "name": "run_python",
        "description": SAMPLE_SPEC.description,
        "input_schema": SAMPLE_SPEC.inputSchema,
    }


def test_openai_tool_schema_wraps_in_function() -> None:
    schema = OpenAIProvider(LLMConfig()).toolSchema(SAMPLE_SPEC)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "run_python"
    assert schema["function"]["parameters"] == SAMPLE_SPEC.inputSchema


def test_xai_inherits_openai_schema_shape() -> None:
    schema = XAIProvider(LLMConfig()).toolSchema(SAMPLE_SPEC)
    assert schema["type"] == "function"
    assert schema["function"]["parameters"] == SAMPLE_SPEC.inputSchema


def test_google_tool_schema_uses_parameters_key() -> None:
    schema = GoogleProvider(LLMConfig()).toolSchema(SAMPLE_SPEC)
    assert schema["name"] == "run_python"
    assert "parameters" in schema
    assert "input_schema" not in schema


def test_ollama_tool_schema_matches_openai_shape() -> None:
    schema = OllamaProvider(LLMConfig()).toolSchema(SAMPLE_SPEC)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "run_python"


def test_tool_specs_factory_returns_provider_native_shape() -> None:
    from dartlab.ai.tools.registry import toolSpecs

    raw = toolSpecs()
    anthropic_specs = toolSpecs(provider="anthropic")
    openai_specs = toolSpecs(provider="openai")

    assert len(raw) == len(anthropic_specs) == len(openai_specs)
    assert all("input_schema" in s for s in anthropic_specs)
    assert all(s.get("type") == "function" for s in openai_specs)


def test_workbench_whitelist_matches_ssot() -> None:
    from dartlab.ai.tools.registry import WORKBENCH_TOOLS

    assert WORKBENCH_TOOLS == (
        "run_python",
        "read_skill",
        "read_capability",
        "web_search",
        "save_artifact",
        "propose_skill",
    )


def test_dartlab_adapter_runs_without_credentials() -> None:
    provider = create_provider(LLMConfig(provider="dartlab", model="research"))
    assert provider.check_available() is True
    events = list(provider.complete(messages=[], tools=[], stream=False))
    assert events and events[-1].kind == "stop"


def test_keyless_adapters_report_unavailable() -> None:
    """API 키 없이 외부 어댑터를 호출하면 check_available 가 False."""

    import os

    os.environ.pop("ANTHROPIC_API_KEY", None)
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GOOGLE_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ.pop("XAI_API_KEY", None)

    assert create_provider(LLMConfig(provider="anthropic")).check_available() is False
    assert create_provider(LLMConfig(provider="openai")).check_available() is False
    assert create_provider(LLMConfig(provider="google")).check_available() is False
    assert create_provider(LLMConfig(provider="xai")).check_available() is False
