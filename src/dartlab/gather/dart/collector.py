"""DART panel collection status compatibility module.

DART disclosure text SSOT is ``data/dart/panel``. The retired document parquet
collectors are intentionally not exposed here; this module only preserves the
status-helper import path used by CLI commands.
"""

from __future__ import annotations

from dartlab.gather.dart.collectorStatus import (
    collectionStats,
    iterUncollected,
    iterUncollectedKind,
    listUncollected,
    listUncollectedKind,
)

__all__ = [
    "collectionStats",
    "iterUncollected",
    "iterUncollectedKind",
    "listUncollected",
    "listUncollectedKind",
]
