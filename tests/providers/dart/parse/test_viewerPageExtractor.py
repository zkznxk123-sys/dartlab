"""providers/dart/parse/viewerPageExtractor.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.parse.viewerPageExtractor  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_html_to_text_callable() -> None:
    """htmlToText() callable smoke."""
    from dartlab.providers.dart.parse.viewerPageExtractor import htmlToText

    assert callable(htmlToText)


def test_parse_sub_docs_callable() -> None:
    """parseSubDocs() callable smoke."""
    from dartlab.providers.dart.parse.viewerPageExtractor import parseSubDocs

    assert callable(parseSubDocs)


def test_table_to_markdown_callable() -> None:
    """tableToMarkdown() callable smoke."""
    from dartlab.providers.dart.parse.viewerPageExtractor import tableToMarkdown

    assert callable(tableToMarkdown)
