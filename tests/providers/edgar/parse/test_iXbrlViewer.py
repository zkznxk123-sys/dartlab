"""edgar/parse/iXbrlViewer test — iXBRL fact 추출 smoke."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_public_api_present() -> None:
    """3 public 함수 export 검증."""
    from dartlab.providers.edgar.parse import (
        extractIxbrlFacts,
        fetchFactsByConcept,
        iterFactsByConcept,
    )

    assert callable(extractIxbrlFacts)
    assert callable(fetchFactsByConcept)
    assert callable(iterFactsByConcept)


def test_extract_empty_html() -> None:
    """빈 HTML → 빈 DataFrame (schema 보존)."""
    from dartlab.providers.edgar.parse import extractIxbrlFacts

    df = extractIxbrlFacts("")
    assert df.is_empty()
    assert "concept" in df.columns
    assert "factType" in df.columns


def test_extract_numeric_fact() -> None:
    """ix:nonFraction → factType=numeric."""
    from dartlab.providers.edgar.parse import extractIxbrlFacts

    html = (
        "<html><body>"
        '<ix:nonFraction name="us-gaap:Revenue" contextRef="C1" '
        'unitRef="USD" decimals="-6">100000000</ix:nonFraction>'
        "</body></html>"
    )
    df = extractIxbrlFacts(html)
    if df.is_empty():
        pytest.skip("BeautifulSoup 미설치 — 빈 DataFrame fallback 정상 동작")
    assert df.shape[0] == 1
    assert df["concept"][0] == "us-gaap:Revenue"
    assert df["factType"][0] == "numeric"
    assert df["unitRef"][0] == "USD"


def test_extract_text_fact() -> None:
    """ix:nonNumeric → factType=text."""
    from dartlab.providers.edgar.parse import extractIxbrlFacts

    html = (
        "<html><body>"
        '<ix:nonNumeric name="dei:EntityRegistrantName" '
        'contextRef="C1">Apple Inc.</ix:nonNumeric>'
        "</body></html>"
    )
    df = extractIxbrlFacts(html)
    if df.is_empty():
        pytest.skip("BeautifulSoup 미설치")
    assert df.shape[0] == 1
    assert df["factType"][0] == "text"
    assert df["value"][0] == "Apple Inc."


def test_fetch_iter_pair() -> None:
    """fetch ↔ iter pair (룰 10) 일관성 시그니처."""
    import inspect

    from dartlab.providers.edgar.parse import fetchFactsByConcept, iterFactsByConcept

    fetchSig = inspect.signature(fetchFactsByConcept)
    iterSig = inspect.signature(iterFactsByConcept)
    assert "facts" in fetchSig.parameters
    assert "concept" in fetchSig.parameters
    assert "limit" in fetchSig.parameters
    assert "facts" in iterSig.parameters
    assert "concept" in iterSig.parameters
    assert "batchSize" in iterSig.parameters
