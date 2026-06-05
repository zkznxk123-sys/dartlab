"""EDGAR panel mapper facade — DART ``panel.mapper`` analog at the same package depth."""

from __future__ import annotations

from dartlab.providers.edgar.panel.build.mapper import (
    ITEM_NAMES_10K,
    ITEM_NAMES_10Q,
    STMT_LABELS,
    canonicalItem,
    captionToStatement,
    contextToCell,
    edgarSectionStatus,
    periodFromReport,
    roleToStatement,
)

__all__ = [
    "ITEM_NAMES_10K",
    "ITEM_NAMES_10Q",
    "STMT_LABELS",
    "canonicalItem",
    "captionToStatement",
    "contextToCell",
    "edgarSectionStatus",
    "periodFromReport",
    "roleToStatement",
]
