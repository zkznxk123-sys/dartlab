"""providers/dart/builder/docsSelectMatcher.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.docsSelectMatcher  # noqa: F401


def test_build_docs_item_index_callable() -> None:
    """buildDocsItemIndex() callable smoke."""
    from dartlab.providers.dart.builder.docsSelectMatcher import buildDocsItemIndex

    assert callable(buildDocsItemIndex)


def test_select_from_docs_topic_callable() -> None:
    """selectFromDocsTopic() callable smoke."""
    from dartlab.providers.dart.builder.docsSelectMatcher import selectFromDocsTopic

    assert callable(selectFromDocsTopic)


def test_select_from_docs_topic_all_callable() -> None:
    """selectFromDocsTopicAll() callable smoke."""
    from dartlab.providers.dart.builder.docsSelectMatcher import selectFromDocsTopicAll

    assert callable(selectFromDocsTopicAll)
