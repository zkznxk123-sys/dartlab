"""providers/dart/openapi/allFilingsCollector.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.allFilingsCollector  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_collect_meta_day_callable() -> None:
    """collectMetaDay() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaDay

    assert callable(collectMetaDay)


def test_collect_meta_range_callable() -> None:
    """collectMetaRange() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectMetaRange

    assert callable(collectMetaRange)


def test_collected_dates_callable() -> None:
    """collectedDates() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import collectedDates

    assert callable(collectedDates)


def test_fill_content_callable() -> None:
    """fillContent() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import fillContent

    assert callable(fillContent)


def test_fill_content_all_callable() -> None:
    """fillContentAll() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import fillContentAll

    assert callable(fillContentAll)


def test_load_all_callable() -> None:
    """loadAll() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import loadAll

    assert callable(loadAll)


def test_load_day_callable() -> None:
    """loadDay() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import loadDay

    assert callable(loadDay)


def test_pending_dates_callable() -> None:
    """pendingDates() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import pendingDates

    assert callable(pendingDates)


def test_stats_callable() -> None:
    """stats() callable smoke."""
    from dartlab.providers.dart.openapi.allFilingsCollector import stats

    assert callable(stats)
