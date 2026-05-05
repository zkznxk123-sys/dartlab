"""Provider 카탈로그 + WorkbenchProvider 진입점 회귀."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_available_providers_lists_catalog_excluding_anthropic():
    from dartlab.ai.providers import available_providers

    names = set(available_providers())
    # 정식 1 순위
    assert "oauth-codex" in names
    # OpenAI 호환 군
    assert {"openai", "ollama", "custom", "groq", "cerebras", "mistral", "gemini", "codex"}.issubset(names)
    # ToS 회피
    assert "anthropic" not in names
    assert "claude" not in names


def test_create_provider_dartlab_returns_unavailable():
    """provider='dartlab' 은 카탈로그에 없으므로 UnavailableProvider 반환."""
    from dartlab.ai.providers import UnavailableProvider, create_provider
    from dartlab.ai.settings.types import LLMConfig

    provider = create_provider(LLMConfig(provider="dartlab", model="research"))
    assert isinstance(provider, UnavailableProvider)
    assert provider.check_available() is False


def test_create_provider_chatgpt_alias_blocked():
    from dartlab.ai.providers import create_provider

    with pytest.raises(ValueError):
        create_provider(provider="chatgpt")


def test_configure_role_binding_changes_resolved_config():
    from dartlab.ai import configure, get_config

    configure(provider="ollama", model="base")
    configure(provider="ollama", model="summary-model", role="summary")

    analysis = get_config()
    summary = get_config(role="summary")

    assert analysis.provider == "ollama"
    assert analysis.model == "base"
    assert summary.provider == "ollama"
    assert summary.model == "summary-model"


def test_provider_config_round_trip_preserves_model():
    from dartlab.ai.providers import OpenAICompatibleProvider, ProviderConfig, create_provider

    provider = create_provider(ProviderConfig(provider="ollama", model="custom-model"))
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.resolved_model == "custom-model"
