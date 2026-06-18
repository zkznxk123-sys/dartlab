"""providers/dart/search/fieldIndex.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.search.fieldIndex  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_content_segment_callable() -> None:
    """buildContentSegment() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import buildContentSegment

    assert callable(buildContentSegment)


def test_clear_cache_callable() -> None:
    """clearCache() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import clearCache

    assert callable(clearCache)


def test_content_stats_callable() -> None:
    """contentStats() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import contentStats

    assert callable(contentStats)


def test_iter_content_callable() -> None:
    """iterContent() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import iterContent

    assert callable(iterContent)


def test_load_segment_callable() -> None:
    """loadSegment() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import loadSegment

    assert callable(loadSegment)


def test_pull_content_index_callable() -> None:
    """pullContentIndex() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import pullContentIndex

    assert callable(pullContentIndex)


def test_push_content_index_callable() -> None:
    """pushContentIndex() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import pushContentIndex

    assert callable(pushContentIndex)


def test_rebuild_content_delta_retired() -> None:
    """delta 세그먼트 폐기(compact-only) — rebuildContentDelta 는 NotImplementedError 로 repoint."""
    import pytest

    from dartlab.providers.dart.search.api import rebuildContentDelta

    with pytest.raises(NotImplementedError):
        rebuildContentDelta()


def test_rebuild_main_callable() -> None:
    """rebuildMain() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import rebuildMain

    assert callable(rebuildMain)


def test_save_segment_callable() -> None:
    """compact-only writer 스모크 — writeSegmentCompanions(동반물) + saveSegmentWithSidecar(=SSOT)."""
    from dartlab.providers.dart.search.fieldIndex import saveSegmentWithSidecar, writeSegmentCompanions

    assert callable(writeSegmentCompanions)
    assert callable(saveSegmentWithSidecar)


def test_search_content_callable() -> None:
    """searchContent() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import searchContent

    assert callable(searchContent)


def test_tokenize_content_callable() -> None:
    """tokenizeContent() callable smoke."""
    from dartlab.providers.dart.search.fieldIndex import tokenizeContent

    assert callable(tokenizeContent)
