"""[shim] synth/strategyRules → quant/strategyRules 도메인 복귀 (0.10 까지 BC)."""

from __future__ import annotations


def __getattr__(name: str):
    """0.10 BC — 사용 시점에 quant/strategyRules 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.quant.screen.strategyRules")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.synth.strategyRules' has no attribute {name!r}") from exc
