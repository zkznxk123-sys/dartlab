"""gather/edgar/search.py mirror smoke — SEC EDGAR Full-Text Search fetch.

수집 일원화: efts.sec.gov 호출(fetch)은 gather 전담. providers/edgar/search 는
lazy ``__getattr__`` re-export shim 으로 공개명만 보존.
"""

import inspect

import pytest

pytestmark = pytest.mark.unit


def test_imports():
    try:
        import dartlab.gather.edgar.search  # noqa: F401
    except ImportError as e:
        pytest.skip(f"module import requires data/env: {e}")


def test_public_api_present() -> None:
    """search / fetchHits / iterHits 3 public 함수 export 검증."""
    from dartlab.gather.edgar.search import fetchHits, iterHits, search

    assert callable(search)
    assert callable(fetchHits)
    assert callable(iterHits)


def test_search_signature() -> None:
    """search 시그니처 — query 필수 + limit/cik/forms/dateRange keyword."""
    from dartlab.gather.edgar.search import search

    params = inspect.signature(search).parameters
    assert "query" in params
    assert "limit" in params
    assert "cik" in params
    assert "forms" in params
    assert "dateRange" in params


def test_providers_shim_resolves_to_gather() -> None:
    """providers/edgar/search lazy shim → gather/edgar/search (providers↛gather seam)."""
    from dartlab.gather.edgar.search import search as gatherSearch
    from dartlab.providers.edgar.search import search as shimSearch

    assert shimSearch is gatherSearch
