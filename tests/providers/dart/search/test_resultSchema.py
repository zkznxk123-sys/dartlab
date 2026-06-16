"""providers/dart/search/resultSchema.py mirror tests."""

from __future__ import annotations

import polars as pl


def test_result_schema_import_and_empty() -> None:
    from dartlab.providers.dart.search.resultSchema import normalizeSearchResult

    assert normalizeSearchResult(pl.DataFrame()).height == 0
