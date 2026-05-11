"""[shim] core/cross/portfolioMapping → quant/portfolioMapping 도메인 복귀 (0.10 까지 BC)."""

from __future__ import annotations


def __getattr__(name: str):
    """0.10 BC — 사용 시점에 quant/portfolioMapping 동적 lookup."""
    import importlib

    mod = importlib.import_module("dartlab.quant.portfolio.mapping")
    try:
        return getattr(mod, name)
    except AttributeError as exc:
        raise AttributeError(f"module 'dartlab.core.cross.portfolioMapping' has no attribute {name!r}") from exc
