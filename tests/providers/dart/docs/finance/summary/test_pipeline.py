"""providers/dart/docs/finance/summary/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.summary.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_fs_summary_callable() -> None:
    """fsSummary() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.pipeline import fsSummary

    assert callable(fsSummary)


def test_load_year_data_callable() -> None:
    """loadYearData() callable smoke."""
    from dartlab.providers.dart.docs.finance.summary.pipeline import loadYearData

    assert callable(loadYearData)
