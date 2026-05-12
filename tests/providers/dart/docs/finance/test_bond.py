"""providers/dart/docs/finance/bond.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.bond  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_bond_callable() -> None:
    """bond() callable smoke."""
    from dartlab.providers.dart.docs.finance.bond import bond

    assert callable(bond)


def test_parse_bond_table_callable() -> None:
    """parseBondTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.bond import parseBondTable

    assert callable(parseBondTable)
