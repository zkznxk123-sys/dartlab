"""providers/dart/docs/finance/rnd.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.rnd  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import extractTableBlocks

    assert callable(extractTableBlocks)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import parseAmount

    assert callable(parseAmount)


def test_parse_float_callable() -> None:
    """parseFloat() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import parseFloat

    assert callable(parseFloat)


def test_parse_rnd_table_callable() -> None:
    """parseRndTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import parseRndTable

    assert callable(parseRndTable)


def test_rnd_callable() -> None:
    """rnd() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import rnd

    assert callable(rnd)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.rnd import splitCells

    assert callable(splitCells)
