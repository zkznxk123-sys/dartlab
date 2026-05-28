"""viewsContext.py mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy import viewsContext

    assert hasattr(viewsContext, "contextSlices")
    assert hasattr(viewsContext, "splitContextText")
    assert hasattr(viewsContext, "splitMarkdownTable")


def test_split_context_text_callable() -> None:
    """splitContextText() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.viewsContext import splitContextText

    assert callable(splitContextText)


def test_split_markdown_table_callable() -> None:
    """splitMarkdownTable() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.viewsContext import splitMarkdownTable

    assert callable(splitMarkdownTable)


def test_context_slices_callable() -> None:
    """contextSlices() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.viewsContext import contextSlices

    assert callable(contextSlices)
