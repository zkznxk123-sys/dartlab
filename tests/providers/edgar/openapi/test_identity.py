"""providers/edgar/openapi/identity.py mirror smoke — P6."""

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.providers.edgar.openapi.identity  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_iter_issuers_callable() -> None:
    """iterIssuers() callable smoke."""
    from dartlab.providers.edgar.openapi.identity import iterIssuers

    assert callable(iterIssuers)


def test_load_tickers_callable() -> None:
    """loadTickers() callable smoke."""
    from dartlab.providers.edgar.openapi.identity import loadTickers

    assert callable(loadTickers)


def test_resolve_issuer_callable() -> None:
    """resolveIssuer() callable smoke."""
    from dartlab.providers.edgar.openapi.identity import resolveIssuer

    assert callable(resolveIssuer)


def test_search_issuers_callable() -> None:
    """searchIssuers() callable smoke."""
    from dartlab.providers.edgar.openapi.identity import searchIssuers

    assert callable(searchIssuers)
