"""AI provider/profile settings package."""

from dartlab.ai.settings.profile import AiProfileManager, get_profile_manager
from dartlab.ai.settings.provider_catalog import (
    build_provider_catalog,
    cli_provider_choices,
    get_provider_spec,
    normalize_provider,
    provider_choices,
    public_provider_ids,
)
from dartlab.ai.settings.routing import AI_ROLES, DEFAULT_ROLE, normalize_role
from dartlab.ai.settings.secrets import SecretStore, get_secret_store
from dartlab.ai.settings.types import LLMConfig

__all__ = [
    "AI_ROLES",
    "AiProfileManager",
    "DEFAULT_ROLE",
    "SecretStore",
    "build_provider_catalog",
    "cli_provider_choices",
    "get_profile_manager",
    "get_provider_spec",
    "get_secret_store",
    "LLMConfig",
    "normalize_provider",
    "normalize_role",
    "provider_choices",
    "public_provider_ids",
]
