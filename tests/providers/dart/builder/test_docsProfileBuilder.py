"""providers/dart/builder/docsProfileBuilder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    import dartlab.providers.dart.builder.docsProfileBuilder  # noqa: F401


def test_build_sections_callable() -> None:
    """buildSections() callable smoke."""
    from dartlab.providers.dart.builder.docsProfileBuilder import buildSections

    assert callable(buildSections)


def test_chapter_for_topic_callable() -> None:
    """chapterForTopic() callable smoke."""
    from dartlab.providers.dart.builder.docsProfileBuilder import chapterForTopic

    assert callable(chapterForTopic)


def test_chapter_map_callable() -> None:
    """chapterMap() callable smoke."""
    from dartlab.providers.dart.builder.docsProfileBuilder import chapterMap

    assert callable(chapterMap)


def test_profile_table_callable() -> None:
    """profileTable() callable smoke."""
    from dartlab.providers.dart.builder.docsProfileBuilder import profileTable

    assert callable(profileTable)


def test_topic_label_callable() -> None:
    """topicLabel() callable smoke."""
    from dartlab.providers.dart.builder.docsProfileBuilder import topicLabel

    assert callable(topicLabel)
