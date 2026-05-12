"""providers/dart/docs/finance/subsidiary.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.subsidiary  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_subsidiary_table_callable() -> None:
    """parseSubsidiaryTable() callable smoke."""
    from dartlab.providers.dart.docs.finance.subsidiary import parseSubsidiaryTable

    assert callable(parseSubsidiaryTable)


def test_subsidiary_callable() -> None:
    """subsidiary() callable smoke."""
    from dartlab.providers.dart.docs.finance.subsidiary import subsidiary

    assert callable(subsidiary)
