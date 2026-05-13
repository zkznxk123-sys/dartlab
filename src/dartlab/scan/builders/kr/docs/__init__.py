"""Docs-derived KR scan builders.

Capabilities:
    - Owns docs section change detection and docs index builder modules.

Args:
    This package exposes submodules only.

Returns:
    Imported docs builder functions from submodules.

Example:
    >>> from dartlab.scan.builders.kr.docs.changes import buildChanges

Guide:
    Put docs raw parquet transforms here. Keep finance/report builders in their own
    packages.

SeeAlso:
    ``docs.changes`` and ``docs.index``.

Requires:
    Raw docs parquet files under the active data root.

AIContext:
    Makes docs prebuild ownership visible in the package tree.

LLM Specifications:
    AntiPatterns: Do not place finance, report API, or valuation builders here.
    OutputSchema: Submodules produce scan parquet artifacts.
    Prerequisites: Caller invokes concrete builder functions.
    Freshness: Prebuild freshness is controlled by the caller workflow.
    Dataflow: raw docs parquet -> docs builder -> scan parquet artifact.
    TargetMarkets: KR docs prebuilds.
"""

from __future__ import annotations

__all__: list[str] = []
