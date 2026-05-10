"""[shim] ai/settings/provider_catalog → core/providers/registry 이전 (0.10 까지 BC).

본체: src/dartlab/core/providers/registry.py
0.11 release 시 본 shim 제거. 직접 사용처는 `from dartlab.core.providers import ...` 로 갱신.
"""

from dartlab.core.providers.registry import (
    _PROVIDERS,
    AI_ROLES,
    ProviderSpec,
    apiKeySecretName,
    buildProviderCatalog,
    cliProviderChoices,
    getDefaultProvider,
    getProviderSpec,
    normalizeProvider,
    oauthSecretName,
    providerChoices,
    publicProviderIds,
    wiredProviderIds,
)

# snake alias — 0.10 까지 backward-compat shim. 0.11 제거.
api_key_secret_name = apiKeySecretName
build_provider_catalog = buildProviderCatalog
cli_provider_choices = cliProviderChoices
get_provider_spec = getProviderSpec
normalize_provider = normalizeProvider
oauth_secret_name = oauthSecretName
provider_choices = providerChoices
public_provider_ids = publicProviderIds
wired_provider_ids = wiredProviderIds

__all__ = [
    "AI_ROLES",
    "ProviderSpec",
    "_PROVIDERS",
    "apiKeySecretName",
    "buildProviderCatalog",
    "cliProviderChoices",
    "getDefaultProvider",
    "getProviderSpec",
    "normalizeProvider",
    "oauthSecretName",
    "providerChoices",
    "publicProviderIds",
    "wiredProviderIds",
    # snake aliases (deprecated, 0.11 제거)
    "api_key_secret_name",
    "build_provider_catalog",
    "cli_provider_choices",
    "get_provider_spec",
    "normalize_provider",
    "oauth_secret_name",
    "provider_choices",
    "public_provider_ids",
    "wired_provider_ids",
]
