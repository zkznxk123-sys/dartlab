"""[shim] settings/routing → core/providers/routing 이전.

본체: src/dartlab/core/providers/routing.py
0.10 부터 snake alias 제거. 0.11 release 시 본 shim 제거.
"""

from dartlab.core.providers.routing import (  # noqa: F401
    AI_ROLES,
    DEFAULT_ROLE,
    normalizeRole,
)

__all__ = ["AI_ROLES", "DEFAULT_ROLE", "normalizeRole"]
