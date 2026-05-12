"""providers/dart/search/ngramIndex.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.search.ngramIndex  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_ngram_index_callable() -> None:
    """buildNgramIndex() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import buildNgramIndex

    assert callable(buildNgramIndex)


def test_iter_ngram_callable() -> None:
    """iterNgram() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import iterNgram

    assert callable(iterNgram)


def test_ngram_stats_callable() -> None:
    """ngramStats() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import ngramStats

    assert callable(ngramStats)


def test_pull_stem_index_callable() -> None:
    """pullStemIndex() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import pullStemIndex

    assert callable(pullStemIndex)


def test_push_stem_index_callable() -> None:
    """pushStemIndex() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import pushStemIndex

    assert callable(pushStemIndex)


def test_search_ngram_callable() -> None:
    """searchNgram() callable smoke."""
    from dartlab.providers.dart.search.ngramIndex import searchNgram

    assert callable(searchNgram)
