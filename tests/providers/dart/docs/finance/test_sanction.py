"""providers/dart/docs/finance/sanction.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.sanction  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import extractTableBlocks

    assert callable(extractTableBlocks)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import parseAmount

    assert callable(parseAmount)


def test_parse_sanction_table_callable() -> None:
    """parseSanctionTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import parseSanctionTable

    assert callable(parseSanctionTable)


def test_sanction_callable() -> None:
    """sanction() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import sanction

    assert callable(sanction)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.sanction import splitCells

    assert callable(splitCells)
