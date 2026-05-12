"""providers/dart/docs/finance/affiliate/extractor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.affiliate.extractor  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_table_rows_callable() -> None:
    """parseTableRows() callable smoke."""
    from dartlab.providers.dart.docs.finance.affiliate.extractor import parseTableRows

    assert callable(parseTableRows)
