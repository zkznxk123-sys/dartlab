"""providers/edgar/report/outsideDirector.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.outsideDirector  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_outside_director_callable() -> None:
    """extractOutsideDirector() callable smoke."""
    from dartlab.providers.edgar.report.outsideDirector import extractOutsideDirector

    assert callable(extractOutsideDirector)
