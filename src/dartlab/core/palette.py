"""[deprecated path] DartLab 컬러 팔레트 — SSOT 는 `dartlab.viz.palette` 로 이동.

기존 `from dartlab.core.palette import COLORS` 호환을 위한 lazy re-export shim.
신규 코드는 `from dartlab.viz.palette import COLORS, INTENT_MAP, TONE_MAP` 사용.

L0 ← L4 직접 import 회피 위해 `__getattr__` 로 지연 lookup.
"""

from __future__ import annotations

_DEFERRED_EXPORTS = frozenset({"COLORS", "INTENT_MAP", "TONE_MAP"})


def __getattr__(name: str) -> object:
    """BC — 사용 시점에 viz/palette 동적 lookup (cycle 회피)."""
    if name in _DEFERRED_EXPORTS:
        import importlib

        mod = importlib.import_module("dartlab.viz.palette")
        return getattr(mod, name)
    raise AttributeError(f"module 'dartlab.core.palette' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(_DEFERRED_EXPORTS)
