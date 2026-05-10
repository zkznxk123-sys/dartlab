"""Provider helpers shared across CLI commands."""

from __future__ import annotations


def detectProvider() -> str:
    """Return the first available provider (smart detection)."""
    from dartlab.ai.settings.detect import autoDetectProvider

    return autoDetectProvider() or "ollama"
