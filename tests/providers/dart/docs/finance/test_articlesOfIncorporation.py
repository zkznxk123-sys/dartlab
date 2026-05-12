"""providers/dart/docs/finance/articlesOfIncorporation.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.articlesOfIncorporation  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_articles_of_incorporation_callable() -> None:
    """articlesOfIncorporation() callable smoke."""
    from dartlab.providers.dart.docs.finance.articlesOfIncorporation import articlesOfIncorporation

    assert callable(articlesOfIncorporation)


def test_is_separator_row_callable() -> None:
    """isSeparatorRow() callable smoke."""
    from dartlab.providers.dart.docs.finance.articlesOfIncorporation import isSeparatorRow

    assert callable(isSeparatorRow)


def test_parse_articles_changes_callable() -> None:
    """parseArticlesChanges() callable smoke."""
    from dartlab.providers.dart.docs.finance.articlesOfIncorporation import parseArticlesChanges

    assert callable(parseArticlesChanges)


def test_parse_business_purpose_callable() -> None:
    """parseBusinessPurpose() callable smoke."""
    from dartlab.providers.dart.docs.finance.articlesOfIncorporation import parseBusinessPurpose

    assert callable(parseBusinessPurpose)


def test_split_cells_callable() -> None:
    """splitCells() callable smoke."""
    from dartlab.providers.dart.docs.finance.articlesOfIncorporation import splitCells

    assert callable(splitCells)
