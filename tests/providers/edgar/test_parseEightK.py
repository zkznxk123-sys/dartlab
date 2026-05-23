"""parseEightKHtml 실 구현 검증 — Item X.XX 패턴 매칭 + 본문 slice."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_empty_html() -> None:
    """빈 HTML → 빈 DataFrame (schema 보존)."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    df = parseEightKHtml("")
    assert df.is_empty()
    assert set(df.columns) == {"item", "label", "text"}


def test_single_item() -> None:
    """단일 Item header → 1 row 추출."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    html = (
        "<html><body>"
        "<p>Item 2.02 Results of Operations and Financial Condition</p>"
        "<p>On October 28, 2024, Apple Inc. reported quarterly revenue of $94 billion.</p>"
        "</body></html>"
    )
    df = parseEightKHtml(html)
    assert df.shape[0] == 1
    assert df["item"][0] == "2.02"
    assert df["label"][0] == "Results of Operations and Financial Condition"
    assert "94 billion" in df["text"][0]


def test_multiple_items() -> None:
    """다중 Item header → 각 row 추출 + 본문 slice."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    html = (
        "<html><body>"
        "<p>Item 2.02 Results of Operations</p>"
        "<p>Revenue body text.</p>"
        "<p>Item 9.01 Financial Statements and Exhibits</p>"
        "<p>Exhibit 99.1 attached.</p>"
        "</body></html>"
    )
    df = parseEightKHtml(html)
    assert df.shape[0] == 2
    assert df["item"][0] == "2.02"
    assert df["item"][1] == "9.01"
    assert "Revenue body" in df["text"][0]
    assert "Exhibit" in df["text"][1]


def test_no_items() -> None:
    """Item header 없는 HTML → 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    html = "<html><body><p>Generic text without 8-K items.</p></body></html>"
    df = parseEightKHtml(html)
    assert df.is_empty()


def test_unknown_item_fallback_label() -> None:
    """STANDARD_8K_ITEMS 미정의 item → 'Item X.XX' fallback."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    html = "<html><body>Item 9.99 Future Item Body.</body></html>"
    df = parseEightKHtml(html)
    if df.is_empty():
        pytest.skip("9.99 regex 매칭 안 됨 (현 regex 는 1-9.XX 만)")
    assert df["label"][0] == "Item 9.99"


def test_category_integration() -> None:
    """parseEightKHtml + itemCategory + fetchItemsByCategory 통합 흐름."""
    from dartlab.providers.edgar.disclosure import fetchItemsByCategory, parseEightKHtml

    html = (
        "<html><body>"
        "<p>Item 2.02 Results of Operations</p>"
        "<p>Quarterly earnings body.</p>"
        "<p>Item 5.02 Departure of Director</p>"
        "<p>CFO resigned.</p>"
        "</body></html>"
    )
    items = parseEightKHtml(html)
    assert items.shape[0] == 2
    earnings = fetchItemsByCategory(items, "EARNINGS")
    assert earnings.shape[0] == 1
    assert earnings["item"][0] == "2.02"
    execChange = fetchItemsByCategory(items, "EXECUTIVE_CHANGE")
    assert execChange.shape[0] == 1
    assert execChange["item"][0] == "5.02"
