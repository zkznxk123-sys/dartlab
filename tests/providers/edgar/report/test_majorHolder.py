"""providers/edgar/report/majorHolder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.majorHolder  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_major_holder_callable() -> None:
    """extractMajorHolder() callable smoke."""
    from dartlab.providers.edgar.report.majorHolder import extractMajorHolder

    assert callable(extractMajorHolder)
