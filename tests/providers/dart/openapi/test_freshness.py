"""providers/dart/openapi/freshness.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.openapi.freshness  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_check_freshness_callable() -> None:
    """checkFreshness() callable smoke."""
    from dartlab.providers.dart.openapi.freshness import checkFreshness

    assert callable(checkFreshness)


def test_collect_missing_callable() -> None:
    """collectMissing() callable smoke."""
    from dartlab.providers.dart.openapi.freshness import collectMissing

    assert callable(collectMissing)


def test_scan_market_freshness_callable() -> None:
    """scanMarketFreshness() callable smoke."""
    from dartlab.providers.dart.openapi.freshness import scanMarketFreshness

    assert callable(scanMarketFreshness)
