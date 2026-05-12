"""providers/dart/docs/finance/capitalChange/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.capitalChange.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import extractTableBlocks

    assert callable(extractTableBlocks)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import parseAmount

    assert callable(parseAmount)


def test_parse_capital_change_table_callable() -> None:
    """parseCapitalChangeTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import parseCapitalChangeTable

    assert callable(parseCapitalChangeTable)


def test_parse_share_total_table_callable() -> None:
    """parseShareTotalTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import parseShareTotalTable

    assert callable(parseShareTotalTable)


def test_parse_treasury_stock_table_callable() -> None:
    """parseTreasuryStockTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import parseTreasuryStockTable

    assert callable(parseTreasuryStockTable)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.capitalChange.parser import splitCells

    assert callable(splitCells)
