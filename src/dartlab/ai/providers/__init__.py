"""Provider adapter connection point for DartLab AI."""

from __future__ import annotations

from typing import Any

from dartlab.ai.settings.types import LLMConfig

ProviderConfig = LLMConfig


class _ResearchGraphProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.resolved_model = config.model or "dartlab-research-graph"

    def check_available(self) -> bool:
        return True


def create_provider(config: ProviderConfig | dict[str, Any] | None = None) -> _ResearchGraphProvider:
    if isinstance(config, ProviderConfig):
        provider_config = config
    elif isinstance(config, dict):
        provider_config = ProviderConfig(
            **{k: v for k, v in config.items() if k in ProviderConfig.__dataclass_fields__}
        )
    else:
        provider_config = ProviderConfig()
    return _ResearchGraphProvider(provider_config)


def available_providers() -> list[str]:
    return ["dartlab"]
