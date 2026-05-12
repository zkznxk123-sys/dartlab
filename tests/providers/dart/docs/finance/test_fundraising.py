"""providers/dart/docs/finance/fundraising.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.fundraising  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_fundraising_callable() -> None:
    """fundraising() callable smoke."""
    from dartlab.providers.dart.docs.finance.fundraising import fundraising

    assert callable(fundraising)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.fundraising import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.fundraising import parseAmount

    assert callable(parseAmount)


def test_parse_equity_issuance_callable() -> None:
    """parseEquityIssuance() callable smoke."""
    from dartlab.providers.dart.docs.finance.fundraising import parseEquityIssuance

    assert callable(parseEquityIssuance)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.fundraising import splitCells

    assert callable(splitCells)
