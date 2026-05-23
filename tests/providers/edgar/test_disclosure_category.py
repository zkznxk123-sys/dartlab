"""edgar/disclosure 8-K item category helper test."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_item_category_known() -> None:
    """표준 25 item 모두 매핑 존재."""
    from dartlab.providers.edgar.disclosure import STANDARD_8K_ITEMS, itemCategory

    for item in STANDARD_8K_ITEMS:
        cat = itemCategory(item)
        assert cat != "UNKNOWN", f"item {item} → UNKNOWN (매핑 누락)"


def test_item_category_unknown() -> None:
    """미정의 item → UNKNOWN."""
    from dartlab.providers.edgar.disclosure import itemCategory

    assert itemCategory("99.99") == "UNKNOWN"


def test_item_category_earnings() -> None:
    """2.02 = EARNINGS (실적 발표)."""
    from dartlab.providers.edgar.disclosure import itemCategory

    assert itemCategory("2.02") == "EARNINGS"


def test_item_category_executive_change() -> None:
    """5.02 = EXECUTIVE_CHANGE."""
    from dartlab.providers.edgar.disclosure import itemCategory

    assert itemCategory("5.02") == "EXECUTIVE_CHANGE"


def test_fetch_by_category() -> None:
    """item 컬럼 → category 필터."""
    from dartlab.providers.edgar.disclosure import fetchItemsByCategory

    items = pl.DataFrame(
        {
            "item": ["2.02", "5.02", "8.01"],
            "label": ["Results", "Exec Change", "Other"],
            "text": ["", "", ""],
        }
    )
    df = fetchItemsByCategory(items, "EARNINGS")
    assert df.shape[0] == 1
    assert df["item"][0] == "2.02"


def test_iter_pair() -> None:
    """fetchItemsByCategory ↔ iterItemsByCategory pair (룰 10)."""
    import inspect

    from dartlab.providers.edgar.disclosure import fetchItemsByCategory, iterItemsByCategory

    fetchSig = inspect.signature(fetchItemsByCategory)
    iterSig = inspect.signature(iterItemsByCategory)
    assert "items" in fetchSig.parameters
    assert "category" in fetchSig.parameters
    assert "limit" in fetchSig.parameters
    assert "items" in iterSig.parameters
    assert "category" in iterSig.parameters
    assert "batchSize" in iterSig.parameters


def test_empty_input() -> None:
    """빈 입력 → 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import fetchItemsByCategory

    empty = pl.DataFrame(schema={"item": pl.Utf8, "label": pl.Utf8, "text": pl.Utf8})
    df = fetchItemsByCategory(empty, "EARNINGS")
    assert df.is_empty()
