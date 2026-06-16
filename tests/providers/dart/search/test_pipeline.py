"""providers/dart/search/pipeline.py mirror tests."""

from __future__ import annotations


def test_pipeline_import() -> None:
    from dartlab.providers.dart.search.pipeline import exportCatalogRowsForContentIndex, planCatalogDelta

    assert callable(planCatalogDelta)
    assert callable(exportCatalogRowsForContentIndex)


def test_export_catalog_rows_preserves_edgar_period_freshness() -> None:
    from dartlab.providers.dart.search.pipeline import exportCatalogRowsForContentIndex

    df = exportCatalogRowsForContentIndex(
        [
            {
                "source": "edgarPanel",
                "rceptNo": "0001140361-26-010274",
                "period": "2025Q4",
                "sectionLeaf": "10-K",
                "contentRaw": "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 10-K",
            }
        ]
    )
    row = df.row(0, named=True)

    assert row["rcept_dt"] == "20251231"
    assert row["sourceDataAsOf"] == "20251231"
    assert row["source"] == "edgar-panel"
    assert row["section_title"] == "10-K"
    assert row["section_content"] == "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 10-K"
