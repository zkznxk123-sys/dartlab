"""providers/edinet/openapi/saver.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.openapi.saver  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_docs_parquet_callable() -> None:
    """buildDocsParquet() callable smoke."""
    from dartlab.providers.edinet.openapi.saver import buildDocsParquet

    assert callable(buildDocsParquet)


def test_build_finance_parquet_callable() -> None:
    """buildFinanceParquet() callable smoke."""
    from dartlab.providers.edinet.openapi.saver import buildFinanceParquet

    assert callable(buildFinanceParquet)


def test_extract_csv_from_zip_callable() -> None:
    """extractCsvFromZip() callable smoke."""
    from dartlab.providers.edinet.openapi.saver import extractCsvFromZip

    assert callable(extractCsvFromZip)


def test_save_parquet_callable() -> None:
    """saveParquet() callable smoke."""
    from dartlab.providers.edinet.openapi.saver import saveParquet

    assert callable(saveParquet)
