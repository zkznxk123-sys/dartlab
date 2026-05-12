"""providers/edgar/bulk/freshness.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.bulk.freshness  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_inspect_bulk_freshness_callable() -> None:
    """inspectBulkFreshness() callable smoke."""
    from dartlab.providers.edgar.bulk.freshness import inspectBulkFreshness

    assert callable(inspectBulkFreshness)


def test_invalidate_bulk_freshness_callable() -> None:
    """invalidateBulkFreshness() callable smoke."""
    from dartlab.providers.edgar.bulk.freshness import invalidateBulkFreshness

    assert callable(invalidateBulkFreshness)


def test_is_bulk_fresh_callable() -> None:
    """isBulkFresh() callable smoke."""
    from dartlab.providers.edgar.bulk.freshness import isBulkFresh

    assert callable(isBulkFresh)


def test_read_saved_etag_callable() -> None:
    """readSavedEtag() callable smoke."""
    from dartlab.providers.edgar.bulk.freshness import readSavedEtag

    assert callable(readSavedEtag)


def test_touch_bulk_freshness_callable() -> None:
    """touchBulkFreshness() callable smoke."""
    from dartlab.providers.edgar.bulk.freshness import touchBulkFreshness

    assert callable(touchBulkFreshness)
