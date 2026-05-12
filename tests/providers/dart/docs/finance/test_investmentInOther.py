"""providers/dart/docs/finance/investmentInOther.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.investmentInOther  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_investment_in_other_callable() -> None:
    """investmentInOther() callable smoke."""
    from dartlab.providers.dart.docs.finance.investmentInOther import investmentInOther

    assert callable(investmentInOther)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.investmentInOther import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.investmentInOther import parseAmount

    assert callable(parseAmount)


def test_parse_investments_callable() -> None:
    """parseInvestments() callable smoke."""
    from dartlab.providers.dart.docs.finance.investmentInOther import parseInvestments

    assert callable(parseInvestments)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.investmentInOther import splitCells

    assert callable(splitCells)
