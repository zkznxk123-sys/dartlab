"""providers/edgar/docs/fetch.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.fetch  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_edgar_collectible_universe_callable() -> None:
    """buildEdgarCollectibleUniverse() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import buildEdgarCollectibleUniverse

    assert callable(buildEdgarCollectibleUniverse)


def test_download_listed_edgar_docs_callable() -> None:
    """downloadListedEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import downloadListedEdgarDocs

    assert callable(downloadListedEdgarDocs)


def test_fetch_edgar_docs_callable() -> None:
    """fetchEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import fetchEdgarDocs

    assert callable(fetchEdgarDocs)


def test_iter_edgar_docs_callable() -> None:
    """iterEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import iterEdgarDocs

    assert callable(iterEdgarDocs)


def test_prepare_edgar_collectible_universe_callable() -> None:
    """prepareEdgarCollectibleUniverse() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import prepareEdgarCollectibleUniverse

    assert callable(prepareEdgarCollectibleUniverse)


def test_summarize_edgar_docs_frame_callable() -> None:
    """summarizeEdgarDocsFrame() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import summarizeEdgarDocsFrame

    assert callable(summarizeEdgarDocsFrame)


def test_summarize_edgar_docs_parquet_callable() -> None:
    """summarizeEdgarDocsParquet() callable smoke."""
    from dartlab.providers.edgar.docs.fetch import summarizeEdgarDocsParquet

    assert callable(summarizeEdgarDocsParquet)
