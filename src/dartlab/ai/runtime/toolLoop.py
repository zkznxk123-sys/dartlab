"""Compatibility shim for the removed legacy tool-calling loop.

The official ask path is ``dartlab.ai.kernel.runAsk``.  This module is
intentionally small so old imports fail loudly instead of silently
reintroducing the retired architecture.
"""

from __future__ import annotations

from typing import Any

from dartlab.ai.runtime.workspace_visual import isMeaningfulVisualSpec

_LEGACY_MESSAGE = "runtime.toolLoop is retired. Use dartlab.ask() or dartlab.ai.kernel.runAsk()."


def streamWithTools(*_args: Any, **_kwargs: Any) -> Any:
    """Legacy entry point kept only to make stale imports explicit."""
    raise RuntimeError(_LEGACY_MESSAGE)


def executeTool(*_args: Any, **_kwargs: Any) -> Any:
    """Legacy engine-tool execution is no longer an AI runtime path."""
    raise RuntimeError(_LEGACY_MESSAGE)


def _cleanFinalText(text: str) -> str:
    """Return text with legacy chart/event marker noise removed."""
    lines = []
    for line in str(text or "").splitlines():
        if "<!--DARTLAB_VIZ:" in line:
            continue
        if line.strip().startswith("[chart:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _autoChartSpec(result: Any, *_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
    """Compatibility helper; only accepts already meaningful visual specs."""
    if isinstance(result, dict) and isMeaningfulVisualSpec(result):
        return result
    return None


def _resolveToolChoice(*_args: Any, **_kwargs: Any) -> str:
    """Legacy callers should not force tool choice in workspace-native mode."""
    return "auto"


def _toolBudgetBypass(*_args: Any, **_kwargs: Any) -> bool:
    return False


def _macroFxAutoArgs(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    return {}


def _cashflowPreflightCalls(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    return []


def _comparisonPreflightCalls(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    return []


def _scanPreflightCalls(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    return []
