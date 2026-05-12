"""[shim] settings/secrets → core/providers/secrets 이전.

본체: src/dartlab/core/providers/secrets.py
0.10 부터 snake alias 제거. 0.11 release 시 본 shim 제거.
"""

from dartlab.reference.providers.secrets import (  # noqa: F401
    SecretEntry,
    SecretStore,
    SecretStoreError,
    getSecretStore,
)

__all__ = [
    "SecretEntry",
    "SecretStore",
    "SecretStoreError",
    "getSecretStore",
]
