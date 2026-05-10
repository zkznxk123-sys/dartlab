"""DartLab AI public entry points."""

from __future__ import annotations

from typing import Any

from dartlab.ai.settings.types import LLMConfig

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
    try:
        from dartlab.ai.settings import get_profile_manager, get_provider_spec, normalize_provider, normalize_role

        normalized = normalize_provider(provider) or provider
        if get_provider_spec(normalized) is not None:
            get_profile_manager().update(
                provider=normalized,
                role=normalize_role(str(role)) if role else None,
                model=config.model,
                base_url=config.base_url,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                system_prompt=config.system_prompt,
                updated_by="compat",
            )
    except (OSError, RuntimeError, ValueError):
        pass
    return config


def get_config(provider: str | None = None, role: str | None = None, **kwargs: Any) -> ProviderConfig:
    """Return provider settings without owning the AI workbench loop."""

    base = (_ROLE_CONFIGS.get(str(role)) if role else None) or _CONFIG
    resolved: dict[str, Any] = {}
    if provider is not None or base.provider != "dartlab":
        try:
            from dartlab.ai.settings import get_profile_manager

            resolved = get_profile_manager().resolve(provider, role=role)
        except (OSError, RuntimeError, ValueError):
            resolved = {}
    resolved_provider = provider or resolved.get("provider") or base.provider
    # 모델 우선순위:
    #   1. 호출자 explicit kwarg (아래 for-loop 에서 마지막 덮어씀)
    #   2. configure() 로 저장한 base.model — 사용자 명시 선택, 보존
    #   3. OpenAI family + base.model 미설정 → latest_openai_model()
    #   4. profile_manager 저장 model (server 자동 저장)
    profile_model = resolved.get("model")
    if base.model:
        resolved_model = base.model
    else:
        try:
            from dartlab.ai.settings.modelResolver import is_openai_family_provider, latest_openai_model

            if is_openai_family_provider(resolved_provider):
                resolved_model = latest_openai_model()
            else:
                resolved_model = profile_model
        except (ImportError, OSError, RuntimeError, ValueError):
            resolved_model = profile_model
    values = {
        "provider": resolved_provider,
        "model": resolved_model,
        "api_key": resolved.get("api_key") or base.api_key,
        "base_url": resolved.get("base_url") or base.base_url,
        "temperature": resolved.get("temperature") if resolved.get("temperature") is not None else base.temperature,
        "max_tokens": resolved.get("max_tokens") if resolved.get("max_tokens") is not None else base.max_tokens,
        "system_prompt": resolved.get("system_prompt") or base.system_prompt,
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
