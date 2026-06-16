"""providers/dart/search/memoryCard.py mirror tests."""

from __future__ import annotations

import polars as pl


def test_memory_card_set_import_and_empty() -> None:
    from dartlab.providers.dart.search.memoryCard import buildMemoryCardSet

    assert buildMemoryCardSet(pl.DataFrame())["cards"] == []


def test_memory_card_carries_entity_cards() -> None:
    import json

    from dartlab.providers.dart.search.memoryCard import buildMemoryCards

    entityCards = [{"label": "peer:신도기연", "value": "신도기연(290520)"}]
    df = pl.DataFrame(
        [
            {
                "source": "allFilings",
                "sourceRef": "dart:allFilings:x#section=0",
                "dataAsOf": "20260616",
                "snippet": "한미반도체 HBM 투자",
                "answerable": True,
                "fieldCards": "[]",
                "entityCards": json.dumps(entityCards, ensure_ascii=False),
            }
        ]
    )

    cards = buildMemoryCards(df, query="HBM", limit=1)

    assert cards[0]["entityCards"] == entityCards
