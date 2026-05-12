"""providers/edgar/docs/loader.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.docs.loader  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_ensure_callable() -> None:
    """ensure() callable smoke."""
    from dartlab.providers.edgar.docs.loader import EdgarDocsLoader

    assert hasattr(EdgarDocsLoader, "ensure")


def test_ensure_edgar_docs_callable() -> None:
    """ensureEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.loader import ensureEdgarDocs

    assert callable(ensureEdgarDocs)


def test_get_latest_regular_edgar_filing_callable() -> None:
    """getLatestRegularEdgarFiling() callable smoke."""
    from dartlab.providers.edgar.docs.loader import getLatestRegularEdgarFiling

    assert callable(getLatestRegularEdgarFiling)


def test_get_local_edgar_docs_state_callable() -> None:
    """getLocalEdgarDocsState() callable smoke."""
    from dartlab.providers.edgar.docs.loader import getLocalEdgarDocsState

    assert callable(getLocalEdgarDocsState)


def test_incremental_update_edgar_docs_callable() -> None:
    """incrementalUpdateEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.loader import incrementalUpdateEdgarDocs

    assert callable(incrementalUpdateEdgarDocs)


def test_is_edgar_docs_check_expired_callable() -> None:
    """isEdgarDocsCheckExpired() callable smoke."""
    from dartlab.providers.edgar.docs.loader import isEdgarDocsCheckExpired

    assert callable(isEdgarDocsCheckExpired)


def test_is_edgar_docs_fresh_callable() -> None:
    """isEdgarDocsFresh() callable smoke."""
    from dartlab.providers.edgar.docs.loader import isEdgarDocsFresh

    assert callable(isEdgarDocsFresh)


def test_rebuild_edgar_docs_callable() -> None:
    """rebuildEdgarDocs() callable smoke."""
    from dartlab.providers.edgar.docs.loader import rebuildEdgarDocs

    assert callable(rebuildEdgarDocs)
