"""providers/dart/docs/finance/salesOrder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.salesOrder  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_detect_unit_callable() -> None:
    """detectUnit() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import detectUnit

    assert callable(detectUnit)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import parseAmount

    assert callable(parseAmount)


def test_parse_order_backlog_callable() -> None:
    """parseOrderBacklog() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import parseOrderBacklog

    assert callable(parseOrderBacklog)


def test_parse_sales_table_callable() -> None:
    """parseSalesTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import parseSalesTable

    assert callable(parseSalesTable)


def test_sales_order_callable() -> None:
    """salesOrder() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import salesOrder

    assert callable(salesOrder)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.salesOrder import splitCells

    assert callable(splitCells)
