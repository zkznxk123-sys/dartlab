"""Compatibility shim for the removed code-block reflection agent."""

from __future__ import annotations

from typing import Any


def _reflect_on_answer(provider: Any, messages: list[dict[str, Any]], answer: str) -> str:
    """Backward-compatible reflection helper.

    The workspace-native runtime does not use this as an extra layer, but older
    callers and tests still expect the helper to return a non-empty provider
    revision when explicitly invoked.
    """
    try:
        response = provider.complete(messages)
    except Exception:  # noqa: BLE001
        return answer
    improved = str(getattr(response, "answer", "") or "").strip()
    return improved or answer
