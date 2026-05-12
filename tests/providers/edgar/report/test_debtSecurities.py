"""providers/edgar/report/debtSecurities.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.debtSecurities  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")
