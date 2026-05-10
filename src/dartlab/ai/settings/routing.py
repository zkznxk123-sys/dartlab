"""[shim] ai/settings/routing → core/providers/routing 이전 (0.10 까지 BC).

본체: src/dartlab/core/providers/routing.py
0.11 release 시 본 shim 제거. 직접 사용처는 `from dartlab.core.providers import ...` 로 갱신.
"""

from dartlab.core.providers.routing import (
    AI_ROLES,
    DEFAULT_ROLE,
    normalizeRole,
)

# snake alias — 0.10 까지 backward-compat shim. 0.11 제거.
normalize_role = normalizeRole

__all__ = ["AI_ROLES", "DEFAULT_ROLE", "normalizeRole", "normalize_role"]
