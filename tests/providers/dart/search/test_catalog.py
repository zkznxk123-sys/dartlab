"""providers/dart/search/catalog.py mirror tests."""

from __future__ import annotations


def test_catalog_import() -> None:
    from dartlab.providers.dart.search.catalog import normalizeCatalogRows

    assert callable(normalizeCatalogRows)


def test_catalog_normalizes_edgar_period_freshness() -> None:
    from dartlab.providers.dart.search.catalog import normalizeCatalogRows

    df = normalizeCatalogRows(
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

    assert row["date"] == "20251231"
    assert row["sourceDataAsOf"] == "20251231"
    assert row["sourceRef"] == "edgar:panel:0001140361-26-010274#section=0"
    assert row["title"] == "10-K"
    assert row["searchText"] == "UNITED STATES SECURITIES AND EXCHANGE COMMISSION FORM 10-K"
