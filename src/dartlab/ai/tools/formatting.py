"""Formatting helpers shared by AI tools."""

from __future__ import annotations

from typing import Any


def format_money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_0000_0000_0000:
        return f"{sign}{number / 1_0000_0000_0000:,.1f}조원"
    if number >= 1_0000_0000:
        return f"{sign}{number / 1_0000_0000:,.0f}억원"
    return f"{sign}{number:,.0f}원"


def format_percent(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if number != number:
        return "n/a"
    return f"{number:.1f}%"


def short_text(value: Any, *, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
