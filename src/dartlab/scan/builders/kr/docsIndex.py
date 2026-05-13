"""Compatibility alias for KR docs index builder.

Capabilities:
    - Preserves ``dartlab.scan.builders.kr.docsIndex`` imports.

Args:
    Same as ``docs.index``.

Returns:
    The actual ``docs.index`` module object.

Example:
    >>> from dartlab.scan.builders.kr.docsIndex import buildDocsIndex

Guide:
    New code should import from ``dartlab.scan.builders.kr.docs.index``.

SeeAlso:
    ``dartlab.scan.builders.kr.docs.index``.

Requires:
    No direct requirements beyond the target module.

AIContext:
    Maintains compatibility while docs prebuild ownership is visible in the package tree.

LLM Specifications:
    AntiPatterns: Do not add implementation logic to this facade.
    OutputSchema: Module alias with docs index builder functions.
    Prerequisites: Target module imports successfully.
    Freshness: No data access in facade.
    Dataflow: old import path -> docs.index implementation module.
    TargetMarkets: KR/EDGAR/EDINET docs index compatibility.
"""

from __future__ import annotations

import sys

from dartlab.scan.builders.kr.docs import index as _impl

sys.modules[__name__] = _impl
