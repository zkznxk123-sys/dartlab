"""providers/dart/docs/sections/views.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsLegacy.views  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_block_priority_callable() -> None:
    """blockPriority() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import blockPriority

    assert callable(blockPriority)


def test_build_markdown_blocks_callable() -> None:
    """buildMarkdownBlocks() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import buildMarkdownBlocks

    assert callable(buildMarkdownBlocks)


def test_build_markdown_wide_callable() -> None:
    """buildMarkdownWide() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import buildMarkdownWide

    assert callable(buildMarkdownWide)


def test_classify_content_callable() -> None:
    """classifyContent() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import classifyContent

    assert callable(classifyContent)


def test_context_slices_callable() -> None:
    """contextSlices() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import contextSlices

    assert callable(contextSlices)


def test_is_boilerplate_topic_callable() -> None:
    """isBoilerplateTopic() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import isBoilerplateTopic

    assert callable(isBoilerplateTopic)


def test_is_placeholder_block_callable() -> None:
    """isPlaceholderBlock() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import isPlaceholderBlock

    assert callable(isPlaceholderBlock)


def test_normalize_title_callable() -> None:
    """normalizeTitle() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import normalizeTitle

    assert callable(normalizeTitle)


def test_retrieval_blocks_callable() -> None:
    """retrievalBlocks() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import retrievalBlocks

    assert callable(retrievalBlocks)


def test_save_view_callable() -> None:
    """saveView() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import saveView

    assert callable(saveView)


def test_split_context_text_callable() -> None:
    """splitContextText() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import splitContextText

    assert callable(splitContextText)


def test_split_markdown_blocks_callable() -> None:
    """splitMarkdownBlocks() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import splitMarkdownBlocks

    assert callable(splitMarkdownBlocks)


def test_split_markdown_table_callable() -> None:
    """splitMarkdownTable() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.views import splitMarkdownTable

    assert callable(splitMarkdownTable)
