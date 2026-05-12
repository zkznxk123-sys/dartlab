"""providers/dart/finance/pivot.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.finance.pivot  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_annual_callable() -> None:
    """buildAnnual() callable smoke."""
    from dartlab.providers.dart.finance.pivot import buildAnnual

    assert callable(buildAnnual)


def test_build_cumulative_callable() -> None:
    """buildCumulative() callable smoke."""
    from dartlab.providers.dart.finance.pivot import buildCumulative

    assert callable(buildCumulative)


def test_build_sce_annual_callable() -> None:
    """buildSceAnnual() callable smoke."""
    from dartlab.providers.dart.finance.pivot import buildSceAnnual

    assert callable(buildSceAnnual)


def test_build_sce_matrix_callable() -> None:
    """buildSceMatrix() callable smoke."""
    from dartlab.providers.dart.finance.pivot import buildSceMatrix

    assert callable(buildSceMatrix)


def test_build_timeseries_callable() -> None:
    """buildTimeseries() callable smoke."""
    from dartlab.providers.dart.finance.pivot import buildTimeseries

    assert callable(buildTimeseries)


def test_clear_finance_cache_callable() -> None:
    """clearFinanceCache() callable smoke."""
    from dartlab.providers.dart.finance.pivot import clearFinanceCache

    assert callable(clearFinanceCache)
