"""providers/dart/docs/finance/executivePay/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.executivePay.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executivePay.parser import classifyBlock

    assert callable(classifyBlock)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.executivePay.parser import extractTableBlocks

    assert callable(extractTableBlocks)


def test_parse_pay_by_type_block_callable() -> None:
    """parsePayByTypeBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executivePay.parser import parsePayByTypeBlock

    assert callable(parsePayByTypeBlock)


def test_parse_pay_individual_block_callable() -> None:
    """parsePayIndividualBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executivePay.parser import parsePayIndividualBlock

    assert callable(parsePayIndividualBlock)
