"""providers/dart/search/resultSchema.py mirror tests."""

from __future__ import annotations

import polars as pl


def test_result_schema_import_and_empty() -> None:
    from dartlab.providers.dart.search.resultSchema import normalizeSearchResult

    assert normalizeSearchResult(pl.DataFrame()).height == 0


def test_result_schema_derives_data_as_of_from_dart_receipt() -> None:
    from dartlab.providers.dart.search.resultSchema import normalizeSearchResult

    out = normalizeSearchResult(
        pl.DataFrame(
            {
                "rcept_no": ["20250515001545"],
                "section_order": [0],
                "report_nm": ["분기보고서 (2025.03)"],
            }
        )
    )

    assert out.row(0, named=True)["dataAsOf"] == "20250515"
