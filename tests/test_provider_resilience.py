"""public provider 예외 경계 테스트."""

import importlib.util

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.settings.types import LLMConfig


class TestProviderAdapterBoundary:
    def test_legacy_provider_modules_are_removed(self):
        assert importlib.util.find_spec("dartlab.ai.providers.openaiCompat") is None
        assert importlib.util.find_spec("dartlab.ai.providers.ollama") is None

    def test_research_graph_adapter_is_available(self):
        from dartlab.ai.providers import createProvider

        provider = createProvider(LLMConfig(provider="dartlab", model="research"))

        assert provider.checkAvailable() is True
        assert provider.resolvedModel == "research"

    def test_create_provider_ignores_unknown_dict_keys(self):
        from dartlab.ai.providers import createProvider

        provider = createProvider({"provider": "dartlab", "model": "dict-model", "unknown": "x"})

        assert provider.checkAvailable() is True
        assert provider.resolvedModel == "dict-model"
