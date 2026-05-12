"""providers/edinet/finance/pivot.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edinet.finance.pivot  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_build_timeseries_callable() -> None:
    """buildTimeseries() callable smoke."""
    from dartlab.providers.edinet.finance.pivot import buildTimeseries

    assert callable(buildTimeseries)


def test_detect_accounting_standard_callable() -> None:
    """detectAccountingStandard() callable smoke."""
    from dartlab.providers.edinet.finance.pivot import detectAccountingStandard

    assert callable(detectAccountingStandard)


def test_get_accounting_standard_callable() -> None:
    """getAccountingStandard() callable smoke."""
    from dartlab.providers.edinet.finance.pivot import getAccountingStandard

    assert callable(getAccountingStandard)


def test_get_consolidation_info_callable() -> None:
    """getConsolidationInfo() callable smoke."""
    from dartlab.providers.edinet.finance.pivot import getConsolidationInfo

    assert callable(getConsolidationInfo)
