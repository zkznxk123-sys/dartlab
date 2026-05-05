"""public provider 예외 경계 테스트."""

import importlib.util

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.settings.types import LLMConfig


class TestProviderAdapterBoundary:
    def test_legacy_provider_modules_are_removed(self):
        assert importlib.util.find_spec("dartlab.ai.providers.openai_compat") is None
        assert importlib.util.find_spec("dartlab.ai.providers.ollama") is None

    def test_research_graph_adapter_is_available(self):
        from dartlab.ai.providers import create_provider

        provider = create_provider(LLMConfig(provider="dartlab", model="research"))

        assert provider.check_available() is True
        assert provider.resolved_model == "research"

    def test_create_provider_ignores_unknown_dict_keys(self):
        from dartlab.ai.providers import create_provider

        provider = create_provider({"provider": "dartlab", "model": "dict-model", "unknown": "x"})

        assert provider.check_available() is True
        assert provider.resolved_model == "dict-model"
