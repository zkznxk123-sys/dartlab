"""providers/edgar/report/executivePay.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.executivePay  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_executive_pay_callable() -> None:
    """extractExecutivePay() callable smoke."""
    from dartlab.providers.edgar.report.executivePay import extractExecutivePay

    assert callable(extractExecutivePay)
