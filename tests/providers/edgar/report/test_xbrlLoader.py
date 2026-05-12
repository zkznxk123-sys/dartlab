"""providers/edgar/report/xbrlLoader.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.report.xbrlLoader  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_edgar_finance_path_callable() -> None:
    """edgarFinancePath() callable smoke."""
    from dartlab.providers.edgar.report.xbrlLoader import edgarFinancePath

    assert callable(edgarFinancePath)


def test_load_xbrl_tags_callable() -> None:
    """loadXbrlTags() callable smoke."""
    from dartlab.providers.edgar.report.xbrlLoader import loadXbrlTags

    assert callable(loadXbrlTags)
