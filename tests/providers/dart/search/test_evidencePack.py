"""providers/dart/search/evidencePack.py mirror tests."""

from __future__ import annotations


def test_build_field_cards_import_and_source_ref() -> None:
    from dartlab.providers.dart.search.evidencePack import buildFieldCards

    cards = buildFieldCards({"sourceRef": "news:x", "snippet": "근거"})
    assert cards[0]["value"] == "news:x"


def test_build_chunk_evidence_uses_query_window() -> None:
    from dartlab.providers.dart.search.evidencePack import buildChunkEvidence

    text = "앞" * 120 + " 유상증자 결정 " + "뒤" * 120
    card = buildChunkEvidence({"text": text, "sourceRef": "dart:x#section=0"}, query="유상증자", maxSnippetChars=80)
    assert card["label"] == "chunk"
    assert "유상증자" in card["evidence"]


def test_build_chunk_evidence_prefers_evidence_text_over_snippet() -> None:
    from dartlab.providers.dart.search.evidencePack import buildChunkEvidence

    row = {
        "snippet": "짧은 스니펫",
        "evidenceText": "앞" * 120 + " 공급계약 체결 " + "뒤" * 120,
        "sourceRef": "dart:x#section=0",
    }
    card = buildChunkEvidence(row, query="공급계약", maxSnippetChars=80)
    assert card["value"] == "evidenceText"
    assert "공급계약" in card["evidence"]
