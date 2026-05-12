"""providers/dart/docs/finance/companyHistory.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.companyHistory  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_company_history_callable() -> None:
    """companyHistory() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyHistory import companyHistory

    assert callable(companyHistory)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyHistory import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_history_callable() -> None:
    """parseHistory() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyHistory import parseHistory

    assert callable(parseHistory)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.companyHistory import splitCells

    assert callable(splitCells)
