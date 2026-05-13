"""Compatibility facade for docs changes builder.

Capabilities:
    - Preserves ``dartlab.scan.builders.kr.changes`` imports.

Args:
    Same as ``docs.changes``.

Returns:
    Re-exported docs changes builder functions.

Example:
    >>> from dartlab.scan.builders.kr.changes import buildChanges

Guide:
    New code should import from ``dartlab.scan.builders.kr.docs.changes``.

SeeAlso:
    ``dartlab.scan.builders.kr.docs.changes``.

Requires:
    No direct requirements beyond the target module.

AIContext:
    Keeps backward compatibility while the tree exposes docs ownership.

LLM Specifications:
    AntiPatterns: Do not add implementation logic to this facade.
    OutputSchema: Re-exported callable objects.
    Prerequisites: Target module imports successfully.
    Freshness: No data access in facade.
    Dataflow: old import path -> docs.changes implementation.
    TargetMarkets: KR scan builder compatibility.
"""

from __future__ import annotations

from dartlab.scan.builders.kr.docs.changes import _buildRawChanges, buildChanges

__all__ = ["_buildRawChanges", "buildChanges"]
