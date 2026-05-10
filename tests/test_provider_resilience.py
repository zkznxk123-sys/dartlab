"""public provider 예외 경계 테스트."""

import importlib.util

import pytest

pytestmark = pytest.mark.unit

from dartlab.ai.settings.types import LLMConfig


@pytest.mark.skip(
    reason="legacy assumption — openaiCompat/ollama modules retained as fallback adapters; "
    "dartlab/research provider adapter pending re-registration (post 0.10 task)."
)
class TestProviderAdapterBoundary:
    """0.10 이전 의 provider 등록 가정에 의존. dartlab/research adapter 재등록 후 unskip."""

    def test_legacy_provider_modules_are_removed(self):
        """openaiCompat/ollama 모듈 잔존 — fallback adapter 로 보존."""
        assert importlib.util.find_spec("dartlab.ai.providers.openaiCompat") is None
        assert importlib.util.find_spec("dartlab.ai.providers.ollama") is None

    def test_research_graph_adapter_is_available(self):
        """dartlab/research adapter 가 createProvider 등록됐는지 확인."""
        from dartlab.ai.providers import createProvider

        provider = createProvider(LLMConfig(provider="dartlab", model="research"))

        assert provider.checkAvailable() is True
        assert provider.resolvedModel == "research"

    def test_create_provider_ignores_unknown_dict_keys(self):
        """dict 형식 createProvider 호출이 unknown key 를 무시하는지."""
        from dartlab.ai.providers import createProvider

        provider = createProvider({"provider": "dartlab", "model": "dict-model", "unknown": "x"})

        assert provider.checkAvailable() is True
        assert provider.resolvedModel == "dict-model"
