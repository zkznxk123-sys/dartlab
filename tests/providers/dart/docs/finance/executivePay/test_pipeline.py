"""providers/dart/docs/finance/executivePay/pipeline.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.docs.finance.executivePay.pipeline  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_executive_pay_callable() -> None:
    """executivePay() callable smoke."""
    from dartlab.providers.dart.docs.finance.executivePay.pipeline import executivePay

    assert callable(executivePay)
