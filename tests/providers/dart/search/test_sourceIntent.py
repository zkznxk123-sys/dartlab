"""providers/dart/search/sourceIntent.py mirror tests."""

from __future__ import annotations


def test_source_intent_import_and_policy() -> None:
    from dartlab.providers.dart.search.sourceIntent import detectSourceIntent

    assert detectSourceIntent("뉴스 말고 공시 유상증자").kind == "filing"
