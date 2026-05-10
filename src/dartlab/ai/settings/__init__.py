"""AI provider/profile settings package."""

from dartlab.ai.settings.profile import AiProfileManager, get_profile_manager
from dartlab.ai.settings.providerCatalog import (
    buildProviderCatalog,
    cliProviderChoices,
    getProviderSpec,
    normalizeProvider,
    providerChoices,
    publicProviderIds,
)
from dartlab.ai.settings.routing import AI_ROLES, DEFAULT_ROLE, normalizeRole
from dartlab.ai.settings.secrets import SecretStore, getSecretStore
from dartlab.ai.settings.types import LLMConfig

__all__ = [
    "AI_ROLES",
    "AiProfileManager",
    "DEFAULT_ROLE",
    "SecretStore",
    "buildProviderCatalog",
    "cliProviderChoices",
    "get_profile_manager",
    "getProviderSpec",
    "getSecretStore",
    "LLMConfig",
    "normalizeProvider",
    "normalizeRole",
    "providerChoices",
    "publicProviderIds",
]
