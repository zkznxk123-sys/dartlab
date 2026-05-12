"""[shim] synth/quadrant → quant/quadrant 도메인 복귀 (0.10 까지 BC)."""

from __future__ import annotations


def __getattr__(name: str):
    """0.10 BC — 사용 시점에 quant/quadrant 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.quant.quadrant")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.synth.quadrant' has no attribute {name!r}") from exc
