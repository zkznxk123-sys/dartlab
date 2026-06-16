"""providers/dart/search/memoryCard.py mirror tests."""

from __future__ import annotations

import polars as pl


def test_memory_card_set_import_and_empty() -> None:
    from dartlab.providers.dart.search.memoryCard import buildMemoryCardSet

    assert buildMemoryCardSet(pl.DataFrame())["cards"] == []
