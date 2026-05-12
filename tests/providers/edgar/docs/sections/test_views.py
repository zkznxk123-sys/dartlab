"""providers/edgar/docs/sections/views.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.sections.views  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_markdown_wide_callable() -> None:
    """buildMarkdownWide() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import buildMarkdownWide

    assert callable(buildMarkdownWide)


def test_context_slices_callable() -> None:
    """contextSlices() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import contextSlices

    assert callable(contextSlices)


def test_coverage_callable() -> None:
    """coverage() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import coverage

    assert callable(coverage)


def test_freq_callable() -> None:
    """freq() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import freq

    assert callable(freq)


def test_retrieval_blocks_callable() -> None:
    """retrievalBlocks() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import retrievalBlocks

    assert callable(retrievalBlocks)


def test_sort_periods_callable() -> None:
    """sortPeriods() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import sortPeriods

    assert callable(sortPeriods)


def test_sort_topics_callable() -> None:
    """sortTopics() callable smoke."""
    from dartlab.providers.edgar.docs.sections.views import sortTopics

    assert callable(sortTopics)
