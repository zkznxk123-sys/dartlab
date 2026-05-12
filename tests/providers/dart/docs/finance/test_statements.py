"""providers/dart/docs/finance/statements.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.statements  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_consolidated_content_callable() -> None:
    """extractConsolidatedContent() callable smoke."""
    from dartlab.providers.dart.docs.finance.statements import extractConsolidatedContent

    assert callable(extractConsolidatedContent)


def test_extract_content_callable() -> None:
    """extractContent() callable smoke."""
    from dartlab.providers.dart.docs.finance.statements import extractContent

    assert callable(extractContent)


def test_split_statements_callable() -> None:
    """splitStatements() callable smoke."""
    from dartlab.providers.dart.docs.finance.statements import splitStatements

    assert callable(splitStatements)


def test_statements_callable() -> None:
    """statements() callable smoke."""
    from dartlab.providers.dart.docs.finance.statements import statements

    assert callable(statements)
