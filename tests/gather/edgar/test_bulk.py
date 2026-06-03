"""gather/edgar/bulk.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.core.edgarClient  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_convert_bulk_to_parquets_callable() -> None:
    """convertBulkToParquets() callable smoke."""
    from dartlab.core.edgarClient import convertBulkToParquets

    assert callable(convertBulkToParquets)


def test_download_companyfacts_bulk_callable() -> None:
    """downloadCompanyfactsBulk() callable smoke."""
    from dartlab.core.edgarClient import downloadCompanyfactsBulk

    assert callable(downloadCompanyfactsBulk)


def test_ensure_finance_parquet_callable() -> None:
    """ensureFinanceParquet() callable smoke."""
    from dartlab.core.edgarClient import ensureFinanceParquet

    assert callable(ensureFinanceParquet)


def test_extract_companyfacts_zip_callable() -> None:
    """extractCompanyfactsZip() callable smoke."""
    from dartlab.core.edgarClient import extractCompanyfactsZip

    assert callable(extractCompanyfactsZip)
