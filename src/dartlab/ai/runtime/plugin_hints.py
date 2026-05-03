"""Runtime plugin hint helpers.

The plugin framework exists, but the AI runtime must not recommend package names
that are not verified by an installed registry or an official catalog. Until a
real catalog is added, this module deliberately returns no "missing plugin"
recommendations.
"""

from __future__ import annotations

from typing import Any


def detect_plugin_hints(
    question: str,
    loaded_plugin_names: list[str] | None = None,
) -> list[dict[str, str]]:
    """Return install suggestions for verified missing plugins.

    The previous implementation used a static keyword map such as
    ``dartlab-plugin-price``. Those package names are not guaranteed to exist
    and duplicate built-in capabilities like ``gather`` and ``quant``. Keeping
    the function but returning an empty list preserves the runtime contract
    while preventing hallucinated install commands.
    """
    _ = (question, loaded_plugin_names)
    return []


def format_plugin_hints(hints: list[dict[str, Any]]) -> str | None:
    """Format verified plugin hints for UI display."""
    if not hints:
        return None

    lines = ["확장 플러그인"]
    for hint in hints:
        name = str(hint.get("name") or "").strip()
        description = str(hint.get("description") or "").strip()
        install = str(hint.get("install") or "").strip()
        if not name:
            continue
        line = f"- {name}"
        if description:
            line += f": {description}"
        lines.append(line)
        if install:
            lines.append(f"  설치: `{install}`")

    return "\n".join(lines) if len(lines) > 1 else None
