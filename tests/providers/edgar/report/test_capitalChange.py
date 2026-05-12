"""providers/edgar/report/capitalChange.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.capitalChange  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_extract_capital_change_callable() -> None:
    """extractCapitalChange() callable smoke."""
    from dartlab.providers.edgar.report.capitalChange import extractCapitalChange

    assert callable(extractCapitalChange)
