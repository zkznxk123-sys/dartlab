"""Compatibility alias for KR report field-screen module.

Capabilities:
    - Preserves ``dartlab.scan.builders.kr.fields`` imports and monkeypatch behavior.

Args:
    Same as ``report.fields``.

Returns:
    The actual ``report.fields`` module object.

Example:
    >>> from dartlab.scan.builders.kr.fields import scanFields

Guide:
    New code should import from ``dartlab.scan.builders.kr.report.fields``.

SeeAlso:
    ``dartlab.scan.builders.kr.report.fields``.

Requires:
    No direct requirements beyond the target module.

AIContext:
    Keeps older tests and runtime plugin paths working while the tree shows report
    ownership.

LLM Specifications:
    AntiPatterns: Do not add implementation logic to this facade.
    OutputSchema: Module alias with report field functions and globals.
    Prerequisites: Target module imports successfully.
    Freshness: No data access in facade.
    Dataflow: old import path -> report.fields implementation module.
    TargetMarkets: KR scan field-screen compatibility.
"""

from __future__ import annotations

import sys

from dartlab.scan.builders.kr.report import fields as _impl

sys.modules[__name__] = _impl
