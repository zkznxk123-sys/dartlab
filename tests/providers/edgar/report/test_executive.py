"""providers/edgar/report/executive.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.executive  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_executive_callable() -> None:
    """extractExecutive() callable smoke."""
    from dartlab.providers.edgar.report.executive import extractExecutive

    assert callable(extractExecutive)
