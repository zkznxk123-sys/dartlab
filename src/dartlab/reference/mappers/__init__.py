"""Reference mapper public exports.

Capabilities:
    - Re-exports the unified mapper engine factory and core mapper protocol classes.

Args:
    This package exposes imports only.

Returns:
    Mapper classes and the cached engine factory from submodules.

Example:
    >>> from dartlab.reference.mappers import getEngine
    >>> engine = getEngine()

Guide:
    Keep this package thin. Registration logic belongs in ``engine.py``.

SeeAlso:
    ``engine`` and ``dartlab.core.mapperEngine``.

Requires:
    Mapper engine modules import successfully.

AIContext:
    Maintains the historical public import path while keeping package init free of logic.

LLM Specifications:
    AntiPatterns: Do not instantiate or register mappers in this file.
    OutputSchema: Re-exported mapper protocol classes and factory.
    Prerequisites: Caller imports concrete functions/classes.
    Freshness: No data access in package init.
    Dataflow: package import -> engine/protocol re-export.
    TargetMarkets: Reference mapper consumers.
"""

from __future__ import annotations

from dartlab.core.mapperEngine import BaseMapper, MapperEngine, MapperStats
from dartlab.reference.mappers.engine import getEngine

__all__ = [
    "BaseMapper",
    "MapperEngine",
    "MapperStats",
    "getEngine",
]
