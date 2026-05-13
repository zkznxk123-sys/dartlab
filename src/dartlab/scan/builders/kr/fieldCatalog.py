"""Compatibility alias for KR report field catalog module.

Capabilities:
    - Preserves ``dartlab.scan.builders.kr.fieldCatalog`` imports.

Args:
    Same as ``report.fieldCatalog``.

Returns:
    The actual ``report.fieldCatalog`` module object.

Example:
    >>> from dartlab.scan.builders.kr.fieldCatalog import _catalog

Guide:
    New code should import from ``dartlab.scan.builders.kr.report.fieldCatalog``.

SeeAlso:
    ``dartlab.scan.builders.kr.report.fieldCatalog``.

Requires:
    No direct requirements beyond the target module.

AIContext:
    Maintains compatibility while the tree exposes report catalog ownership.

LLM Specifications:
    AntiPatterns: Do not add catalog rows or parsing logic to this facade.
    OutputSchema: Module alias with catalog functions and constants.
    Prerequisites: Target module imports successfully.
    Freshness: No data access in facade.
    Dataflow: old import path -> report.fieldCatalog implementation module.
    TargetMarkets: KR scan field catalog compatibility.
"""

from __future__ import annotations

import sys

from dartlab.scan.builders.kr.report import fieldCatalog as _impl

sys.modules[__name__] = _impl
