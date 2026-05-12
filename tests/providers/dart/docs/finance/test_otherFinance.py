"""providers/dart/docs/finance/otherFinance.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.otherFinance  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import isSeparatorRow

    assert callable(isSeparatorRow)


def test_other_finance_callable() -> None:
    """otherFinance() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import otherFinance

    assert callable(otherFinance)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import parseAmount

    assert callable(parseAmount)


def test_parse_bad_debt_provision_callable() -> None:
    """parseBadDebtProvision() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import parseBadDebtProvision

    assert callable(parseBadDebtProvision)


def test_parse_inventory_callable() -> None:
    """parseInventory() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import parseInventory

    assert callable(parseInventory)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.otherFinance import splitCells

    assert callable(splitCells)
