"""Report and screen-field KR scan builders.

Capabilities:
    - Owns report API field catalog and condition-screen execution modules.

Args:
    This package exposes submodules only.

Returns:
    Imported report builder and field-screen functions from submodules.

Example:
    >>> from dartlab.scan.builders.kr.report.fields import scanFields

Guide:
    Put report schema/catalog/screen field code here. Keep docs and finance prebuilds in
    their own packages.

SeeAlso:
    ``report.fields`` and ``report.fieldCatalog``.

Requires:
    Optional report prebuild parquet files for schema-derived catalog rows.

AIContext:
    Makes report/screen field ownership visible without breaking the legacy import path.

LLM Specifications:
    AntiPatterns: Do not place docs text index or finance parquet build logic here.
    OutputSchema: Submodules return catalog DataFrames or screen result DataFrames.
    Prerequisites: Caller invokes concrete screen/catalog functions.
    Freshness: Catalog freshness follows available local prebuild schema.
    Dataflow: report/market sources -> field loader -> screen result.
    TargetMarkets: KR scan field screening.
"""

from __future__ import annotations

__all__: list[str] = []
