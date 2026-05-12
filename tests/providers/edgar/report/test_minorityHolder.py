"""providers/edgar/report/minorityHolder.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.minorityHolder  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_minority_holder_callable() -> None:
    """extractMinorityHolder() callable smoke."""
    from dartlab.providers.edgar.report.minorityHolder import extractMinorityHolder

    assert callable(extractMinorityHolder)
