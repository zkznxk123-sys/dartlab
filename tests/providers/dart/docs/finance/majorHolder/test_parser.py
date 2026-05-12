"""providers/dart/docs/finance/majorHolder/parser.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.majorHolder.parser  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_big_holders_callable() -> None:
    """parseBigHolders() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.parser import parseBigHolders

    assert callable(parseBigHolders)


def test_parse_major_holder_table_callable() -> None:
    """parseMajorHolderTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.parser import parseMajorHolderTable

    assert callable(parseMajorHolderTable)


def test_parse_minority_callable() -> None:
    """parseMinority() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.parser import parseMinority

    assert callable(parseMinority)


def test_parse_voting_callable() -> None:
    """parseVoting() callable smoke."""
    from dartlab.providers.dart.docs.finance.majorHolder.parser import parseVoting

    assert callable(parseVoting)
