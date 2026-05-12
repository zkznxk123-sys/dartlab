"""providers/dart/builder/docsIndexBuilder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.docsIndexBuilder  # noqa: F401


def test_index_docs_rows_callable() -> None:
    """indexDocsRows() callable smoke."""
    from dartlab.providers.dart.builder.docsIndexBuilder import indexDocsRows

    assert callable(indexDocsRows)


def test_index_finance_rows_callable() -> None:
    """indexFinanceRows() callable smoke."""
    from dartlab.providers.dart.builder.docsIndexBuilder import indexFinanceRows

    assert callable(indexFinanceRows)


def test_index_report_rows_callable() -> None:
    """indexReportRows() callable smoke."""
    from dartlab.providers.dart.builder.docsIndexBuilder import indexReportRows

    assert callable(indexReportRows)
