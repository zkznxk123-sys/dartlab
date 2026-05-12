"""providers/dart/docs/finance/tangibleAsset/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.tangibleAsset.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_find_movement_tables_callable() -> None:
    """findMovementTables() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import findMovementTables

    assert callable(findMovementTables)


def test_get_total_value_callable() -> None:
    """getTotalValue() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import getTotalValue

    assert callable(getTotalValue)


def test_is_asset_category_callable() -> None:
    """isAssetCategory() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import isAssetCategory

    assert callable(isAssetCategory)


def test_is_description_row_callable() -> None:
    """isDescriptionRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import isDescriptionRow

    assert callable(isDescriptionRow)


def test_is_movement_row_callable() -> None:
    """isMovementRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import isMovementRow

    assert callable(isMovementRow)


def test_normalize_label_callable() -> None:
    """normalizeLabel() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import normalizeLabel

    assert callable(normalizeLabel)


def test_parse_movement_block_callable() -> None:
    """parseMovementBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import parseMovementBlock

    assert callable(parseMovementBlock)


def test_parse_transposed_block_callable() -> None:
    """parseTransposedBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import parseTransposedBlock

    assert callable(parseTransposedBlock)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import splitCells

    assert callable(splitCells)


def test_split_period_blocks_callable() -> None:
    """splitPeriodBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.tangibleAsset.parser import splitPeriodBlocks

    assert callable(splitPeriodBlocks)
