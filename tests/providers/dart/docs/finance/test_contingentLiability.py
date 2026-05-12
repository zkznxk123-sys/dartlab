"""providers/dart/docs/finance/contingentLiability.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.contingentLiability  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import classifyBlock

    assert callable(classifyBlock)


def test_contingent_liability_callable() -> None:
    """contingentLiability() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import contingentLiability

    assert callable(contingentLiability)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import extractTableBlocks

    assert callable(extractTableBlocks)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_amount_callable() -> None:
    """parseAmount() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import parseAmount

    assert callable(parseAmount)


def test_parse_guarantee_detail_callable() -> None:
    """parseGuaranteeDetail() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import parseGuaranteeDetail

    assert callable(parseGuaranteeDetail)


def test_parse_guarantee_summary_callable() -> None:
    """parseGuaranteeSummary() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import parseGuaranteeSummary

    assert callable(parseGuaranteeSummary)


def test_parse_lawsuit_callable() -> None:
    """parseLawsuit() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import parseLawsuit

    assert callable(parseLawsuit)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.contingentLiability import splitCells

    assert callable(splitCells)
