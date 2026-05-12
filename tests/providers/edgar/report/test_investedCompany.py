"""providers/edgar/report/investedCompany.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.investedCompany  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_invested_company_callable() -> None:
    """extractInvestedCompany() callable smoke."""
    from dartlab.providers.edgar.report.investedCompany import extractInvestedCompany

    assert callable(extractInvestedCompany)
