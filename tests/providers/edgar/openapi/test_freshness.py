"""providers/edgar/openapi/freshness.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.freshness  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_check_edgar_freshness_callable() -> None:
    """checkEdgarFreshness() callable smoke."""
    from dartlab.providers.edgar.openapi.freshness import checkEdgarFreshness

    assert callable(checkEdgarFreshness)


def test_collect_edgar_missing_callable() -> None:
    """collectEdgarMissing() callable smoke."""
    from dartlab.providers.edgar.openapi.freshness import collectEdgarMissing

    assert callable(collectEdgarMissing)


def test_scan_edgar_market_freshness_callable() -> None:
    """scanEdgarMarketFreshness() callable smoke."""
    from dartlab.providers.edgar.openapi.freshness import scanEdgarMarketFreshness

    assert callable(scanEdgarMarketFreshness)
