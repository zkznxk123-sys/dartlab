"""providers/dart/docs/finance/dividend.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.dividend  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_dividend_callable() -> None:
    """dividend() callable smoke."""
    from dartlab.providers.dart.docs.finance.dividend import dividend

    assert callable(dividend)


def test_parse_dividend_table_callable() -> None:
    """parseDividendTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.dividend import parseDividendTable

    assert callable(parseDividendTable)
