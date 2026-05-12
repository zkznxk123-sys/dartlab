"""providers/dart/docs/finance/relatedPartyTx.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.relatedPartyTx  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import classifyBlock

    assert callable(classifyBlock)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import extractTableBlocks

    assert callable(extractTableBlocks)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import parseAmount

    assert callable(parseAmount)


def test_parse_guarantee_block_callable() -> None:
    """parseGuaranteeBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import parseGuaranteeBlock

    assert callable(parseGuaranteeBlock)


def test_parse_revenue_tx_block_callable() -> None:
    """parseRevenueTxBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import parseRevenueTxBlock

    assert callable(parseRevenueTxBlock)


def test_related_party_tx_callable() -> None:
    """relatedPartyTx() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import relatedPartyTx

    assert callable(relatedPartyTx)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.relatedPartyTx import splitCells

    assert callable(splitCells)
