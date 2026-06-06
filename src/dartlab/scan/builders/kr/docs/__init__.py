"""Panel-derived KR disclosure scan builders.

Capabilities:
    - Owns disclosure section change detection and docs-index builder modules.

Args:
    This package exposes submodules only.

Returns:
    Imported docs builder functions from submodules.

Example:
    >>> from dartlab.scan.builders.kr.docs.changes import buildChanges

Guide:
    Put panel-derived disclosure transforms here. Keep finance/report builders in their own packages.

SeeAlso:
    ``docs.changes`` and ``docs.index``.

Requires:
    Panel parquet files under the active data root.

AIContext:
    Makes disclosure prebuild ownership visible in the package tree.

LLM Specifications:
    AntiPatterns: Do not place finance, report API, or valuation builders here.
    OutputSchema: Submodules produce scan parquet artifacts.
    Prerequisites: Caller invokes concrete builder functions.
    Freshness: Prebuild freshness is controlled by the caller workflow.
    Dataflow: panel parquet -> docs-index builder -> scan parquet artifact.
    TargetMarkets: KR disclosure prebuilds.
"""

from __future__ import annotations

__all__: list[str] = []
