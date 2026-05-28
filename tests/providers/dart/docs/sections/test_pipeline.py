"""providers/dart/docs/sections/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.sectionsLegacy.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_clear_prepared_cache_callable() -> None:
    """clearPreparedCache() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import clearPreparedCache

    assert callable(clearPreparedCache)


def test_iter_period_subsets_callable() -> None:
    """iterPeriodSubsets() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import iterPeriodSubsets

    assert callable(iterPeriodSubsets)


def test_sections_callable() -> None:
    """sections() callable smoke."""
    from dartlab.providers.dart.docs.sectionsLegacy.pipeline import sections

    assert callable(sections)
