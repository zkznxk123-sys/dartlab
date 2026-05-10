"""[shim] core/cross/scenario → macro/scenario 도메인 복귀 (0.10 까지 BC).

본체: src/dartlab/macro/scenario.py
__getattr__ 동적 lookup — module-level import 0 (cycle 안 만듦). 0.11 제거.
"""

from __future__ import annotations


def __getattr__(name: str):
    """0.10 BC — 사용 시점에 macro/scenario 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.macro.scenario")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.core.cross.scenario' has no attribute {name!r}") from exc
