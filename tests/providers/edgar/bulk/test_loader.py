"""providers/edgar/bulk/loader.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.bulk.loader  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_ensure_callable() -> None:
    """ensure() callable smoke."""
    from dartlab.providers.edgar.bulk.loader import EdgarBulkLoader

    assert hasattr(EdgarBulkLoader, "ensure")


def test_register_edgar_bulk_loader_callable() -> None:
    """registerEdgarBulkLoader() callable smoke."""
    from dartlab.providers.edgar.bulk.loader import registerEdgarBulkLoader

    assert callable(registerEdgarBulkLoader)
