"""providers/dart/docs/sections/extractors.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.extractors  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_parse_subtopic_table_callable() -> None:
    """parseSubtopicTable() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.extractors import parseSubtopicTable

    assert callable(parseSubtopicTable)


def test_topic_subtables_callable() -> None:
    """topicSubtables() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.extractors import topicSubtables

    assert callable(topicSubtables)
