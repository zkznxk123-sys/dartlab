"""edgar/search/api wrapper smoke test — public surface 존재 + signature 검증.

실제 SEC API 호출 안 함 (네트워크 의존 회피). vcrpy 또는 fixture 기반 테스트는
별 트랙.
"""

from __future__ import annotations

import inspect

import pytest

pytestmark = pytest.mark.unit


def test_public_api_present() -> None:
    """search / fetchHits / iterHits 3 public 함수 export 검증."""
    from dartlab.providers.edgar.search import fetchHits, iterHits, search

    assert callable(search)
    assert callable(fetchHits)
    assert callable(iterHits)


def test_search_signature() -> None:
    """search 시그니처 — query 필수 + limit/cik/forms/dateRange keyword."""
    from dartlab.providers.edgar.search import search

    sig = inspect.signature(search)
    params = sig.parameters
    assert "query" in params
    assert "limit" in params
    assert "cik" in params
    assert "forms" in params
    assert "dateRange" in params


def test_fetch_iter_pair() -> None:
    """fetchHits ↔ iterHits pair (룰 10) 시그니처 일관성 (limit ↔ pageSize/maxPages)."""
    from dartlab.providers.edgar.search import fetchHits, iterHits

    fetchSig = inspect.signature(fetchHits)
    iterSig = inspect.signature(iterHits)
    assert "query" in fetchSig.parameters
    assert "query" in iterSig.parameters
    # fetch 는 limit, iter 는 pageSize + maxPages
    assert "limit" in fetchSig.parameters
    assert "pageSize" in iterSig.parameters
    assert "maxPages" in iterSig.parameters
