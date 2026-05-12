"""providers/dart/ops/insiderTrades.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.dart.ops.insiderTrades  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_fetch_insider_trading_raw_callable() -> None:
    """fetchInsiderTradingRaw() callable smoke."""
    from dartlab.providers.dart.ops.insiderTrades import fetchInsiderTradingRaw

    assert callable(fetchInsiderTradingRaw)


def test_fetch_major_shareholders_raw_callable() -> None:
    """fetchMajorShareholdersRaw() callable smoke."""
    from dartlab.providers.dart.ops.insiderTrades import fetchMajorShareholdersRaw

    assert callable(fetchMajorShareholdersRaw)


def test_iter_insider_trading_raw_callable() -> None:
    """iterInsiderTradingRaw() callable smoke."""
    from dartlab.providers.dart.ops.insiderTrades import iterInsiderTradingRaw

    assert callable(iterInsiderTradingRaw)


def test_iter_major_shareholders_raw_callable() -> None:
    """iterMajorShareholdersRaw() callable smoke."""
    from dartlab.providers.dart.ops.insiderTrades import iterMajorShareholdersRaw

    assert callable(iterMajorShareholdersRaw)
