"""Provider dispatch — picks an adapter from LLMConfig."""

from __future__ import annotations

from typing import Any

from dartlab.ai.providers.base import LLMProvider
from dartlab.ai.settings.types import LLMConfig

ProviderConfig = LLMConfig

_PROVIDERS = ("anthropic", "openai", "google", "xai", "ollama", "dartlab")


def availableProviders() -> list[str]:
    """availableProviders — TODO 한국어 동작 설명."""
    return list(_PROVIDERS)


def createProvider(config: LLMConfig | dict[str, Any] | None = None) -> LLMProvider:
    """createProvider — TODO 한국어 동작 설명."""
    cfg = _coerceConfig(config)
    name = (cfg.provider or "dartlab").lower()
    if name == "anthropic":
        from dartlab.ai.providers.anthropic import AnthropicProvider

        return AnthropicProvider(cfg)
    if name == "openai":
        from dartlab.ai.providers.openai import OpenAIProvider

        return OpenAIProvider(cfg)
    if name == "google" or name == "gemini":
        from dartlab.ai.providers.google import GoogleProvider

        return GoogleProvider(cfg)
    if name in ("xai", "grok"):
        from dartlab.ai.providers.xai import XAIProvider

        return XAIProvider(cfg)
    if name == "ollama":
        from dartlab.ai.providers.ollama import OllamaProvider

        return OllamaProvider(cfg)
    from dartlab.ai.providers.dartlab import DartLabProvider

    return DartLabProvider(cfg)


_SNAKE_TO_CAMEL_LLM = {
    "api_key": "apiKey",
    "base_url": "baseUrl",
    "max_tokens": "maxTokens",
    "system_prompt": "systemPrompt",
}


def _coerceConfig(config: LLMConfig | dict[str, Any] | None) -> LLMConfig:
    if isinstance(config, LLMConfig):
        return config
    if isinstance(config, dict):
        # 호환: 외부 caller 가 snake_case 키로 전달해도 camelCase 필드로 매핑
        normalized = {_SNAKE_TO_CAMEL_LLM.get(k, k): v for k, v in config.items()}
        allowed = {k: v for k, v in normalized.items() if k in LLMConfig.__dataclass_fields__}
        return LLMConfig(**allowed)
    return LLMConfig()


__all__ = ["availableProviders", "createProvider", "ProviderConfig"]
