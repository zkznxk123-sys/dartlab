"""providers/dart/docs/finance/internalControl.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.internalControl  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.internalControl import extractTableBlocks

    assert callable(extractTableBlocks)


def test_internal_control_callable() -> None:
    """internalControl() callable smoke."""
    from dartlab.providers.dart.docs.finance.internalControl import internalControl

    assert callable(internalControl)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.internalControl import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_internal_control_table_callable() -> None:
    """parseInternalControlTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.internalControl import parseInternalControlTable

    assert callable(parseInternalControlTable)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.internalControl import splitCells

    assert callable(splitCells)
