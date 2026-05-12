"""providers/edgar/finance/pivot.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.finance.pivot  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_annual_callable() -> None:
    """buildAnnual() callable smoke."""
    from dartlab.providers.edgar.finance.pivot import buildAnnual

    assert callable(buildAnnual)


def test_build_sce_callable() -> None:
    """buildSce() callable smoke."""
    from dartlab.providers.edgar.finance.pivot import buildSce

    assert callable(buildSce)


def test_build_timeseries_callable() -> None:
    """buildTimeseries() callable smoke."""
    from dartlab.providers.edgar.finance.pivot import buildTimeseries

    assert callable(buildTimeseries)


def test_get_shares_outstanding_callable() -> None:
    """getSharesOutstanding() callable smoke."""
    from dartlab.providers.edgar.finance.pivot import getSharesOutstanding

    assert callable(getSharesOutstanding)
