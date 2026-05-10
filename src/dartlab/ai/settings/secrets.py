"""[shim] ai/settings/secrets → core/providers/secrets 이전 (0.10 까지 BC).

본체: src/dartlab/core/providers/secrets.py
0.11 release 시 본 shim 제거. 직접 사용처는 `from dartlab.core.providers import ...` 로 갱신.
"""

from dartlab.core.providers.secrets import (
    SecretEntry,
    SecretStore,
    SecretStoreError,
    getSecretStore,
)

# snake alias — 0.10 까지 backward-compat shim. 0.11 제거.
get_secret_store = getSecretStore

__all__ = [
    "SecretEntry",
    "SecretStore",
    "SecretStoreError",
    "getSecretStore",
    "get_secret_store",
]
