"""providers/dart/docs/sections/runtime.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsArchive.runtime  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_apply_projections_callable() -> None:
    """applyProjections() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import applyProjections

    assert callable(applyProjections)


def test_base_chunk_path_callable() -> None:
    """baseChunkPath() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import baseChunkPath

    assert callable(baseChunkPath)


def test_chapter_from_major_num_callable() -> None:
    """chapterFromMajorNum() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import chapterFromMajorNum

    assert callable(chapterFromMajorNum)


def test_chapter_teacher_topics_callable() -> None:
    """chapterTeacherTopics() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import chapterTeacherTopics

    assert callable(chapterTeacherTopics)


def test_detail_topic_for_block_callable() -> None:
    """detailTopicForBlock() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import detailTopicForBlock

    assert callable(detailTopicForBlock)


def test_detail_topic_for_topic_callable() -> None:
    """detailTopicForTopic() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import detailTopicForTopic

    assert callable(detailTopicForTopic)


def test_extract_semantic_units_callable() -> None:
    """extractSemanticUnits() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import extractSemanticUnits

    assert callable(extractSemanticUnits)


def test_projection_suppressed_topics_callable() -> None:
    """projectionSuppressedTopics() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import projectionSuppressedTopics

    assert callable(projectionSuppressedTopics)


def test_semantic_topic_for_block_callable() -> None:
    """semanticTopicForBlock() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import semanticTopicForBlock

    assert callable(semanticTopicForBlock)


def test_semantic_topic_for_label_callable() -> None:
    """semanticTopicForLabel() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import semanticTopicForLabel

    assert callable(semanticTopicForLabel)


def test_split_by_major_heading_callable() -> None:
    """splitByMajorHeading() callable smoke."""
    from dartlab.providers.dart.docs.sectionsArchive.runtime import splitByMajorHeading

    assert callable(splitByMajorHeading)
