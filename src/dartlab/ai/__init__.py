"""DartLab AI public entry points."""

from __future__ import annotations

from typing import Any

from dartlab.core.ai.types import LLMConfig

from .kernel import ask

ProviderConfig = LLMConfig

_CONFIG = LLMConfig()
_ROLE_CONFIGS: dict[str, LLMConfig] = {}


def configure(provider: str = "dartlab", **kwargs: Any) -> ProviderConfig:
    """Configure provider settings for compatibility callers."""

    global _CONFIG
    role = kwargs.pop("role", None)
    values = {"provider": provider, **{k: v for k, v in kwargs.items() if k in ProviderConfig.__dataclass_fields__}}
    config = ProviderConfig(**values)
    if role:
        _ROLE_CONFIGS[str(role)] = config
    else:
        _CONFIG = config
    return config


def get_config(provider: str | None = None, role: str | None = None, **kwargs: Any) -> ProviderConfig:
    """Return provider settings without owning the AI workbench loop."""

    base = (_ROLE_CONFIGS.get(str(role)) if role else None) or _CONFIG
    values = {
        "provider": provider or base.provider,
        "model": base.model,
        "api_key": base.api_key,
        "base_url": base.base_url,
        "temperature": base.temperature,
        "max_tokens": base.max_tokens,
        "system_prompt": base.system_prompt,
    }
    for key, value in kwargs.items():
        if key in values and value is not None:
            values[key] = value
    return ProviderConfig(**values)


def templates(name: str | None = None):
    """Return available analysis templates."""

    items = {"dartlab-research": "Skill OS 근거 기반 DartLab research graph"}
    return items.get(name) if name else items


def saveTemplate(name: str, *, content: str | None = None, file: str | None = None) -> dict[str, str | None]:
    """Acknowledge template save requests until the new template store lands."""

    return {"name": name, "content": content, "file": file}


__all__ = ["ask", "configure", "get_config", "templates", "saveTemplate"]
