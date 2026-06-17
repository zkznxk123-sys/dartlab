"""providers/dart/search/sourceIntent.py mirror tests."""

from __future__ import annotations


def test_source_intent_import_and_policy() -> None:
    from dartlab.providers.dart.search.sourceIntent import detectSourceIntent

    assert detectSourceIntent("뉴스 말고 공시 유상증자").kind == "filing"


def test_body_and_footnote_queries_default_to_filing_intent() -> None:
    from dartlab.providers.dart.search.sourceIntent import detectSourceIntent

    assert detectSourceIntent("법인세 불확실성 주석").kind == "filing"
    assert detectSourceIntent("원재료 가격 상승 위험요인").kind == "filing"
    assert detectSourceIntent("뉴스로 원재료 가격 상승 위험").kind == "news"
