"""providers/dart/docs/finance/executive/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.executive.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_aggregate_executives_callable() -> None:
    """aggregateExecutives() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.parser import aggregateExecutives

    assert callable(aggregateExecutives)


def test_classify_block_callable() -> None:
    """classifyBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.parser import classifyBlock

    assert callable(classifyBlock)


def test_extract_table_blocks_callable() -> None:
    """extractTableBlocks() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.parser import extractTableBlocks

    assert callable(extractTableBlocks)


def test_parse_executive_block_callable() -> None:
    """parseExecutiveBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.parser import parseExecutiveBlock

    assert callable(parseExecutiveBlock)


def test_parse_unregistered_pay_block_callable() -> None:
    """parseUnregisteredPayBlock() callable smoke."""
    from dartlab.providers.dart.docs.finance.executive.parser import parseUnregisteredPayBlock

    assert callable(parseUnregisteredPayBlock)
