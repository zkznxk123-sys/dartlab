"""providers/dart/openapi/collector.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.dart.collector  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_collection_stats_callable() -> None:
    """collectionStats() callable smoke."""
    from dartlab.gather.dart.collector import collectionStats

    assert callable(collectionStats)


def test_iter_uncollected_callable() -> None:
    """iterUncollected() callable smoke."""
    from dartlab.gather.dart.collector import iterUncollected

    assert callable(iterUncollected)


def test_iter_uncollected_kind_callable() -> None:
    """iterUncollectedKind() callable smoke."""
    from dartlab.gather.dart.collector import iterUncollectedKind

    assert callable(iterUncollectedKind)


def test_list_uncollected_callable() -> None:
    """listUncollected() callable smoke."""
    from dartlab.gather.dart.collector import listUncollected

    assert callable(listUncollected)


def test_list_uncollected_kind_callable() -> None:
    """listUncollectedKind() callable smoke."""
    from dartlab.gather.dart.collector import listUncollectedKind

    assert callable(listUncollectedKind)
