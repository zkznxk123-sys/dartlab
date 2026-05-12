"""[shim] settings/providerCatalog → core/providers/registry 이전.

본체: src/dartlab/core/providers/registry.py
0.10 부터 snake alias 제거 (사용자 결정). 모든 사용처 camelCase 갱신 완료.
0.11 release 시 본 shim 제거 예정 — `from dartlab.core.providers import ...` 직접 사용.
"""

from dartlab.core.providers.registry import (  # noqa: F401
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
]
