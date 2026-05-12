"""extractor.py mirror test."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.edgar.docs.sections import extractor

    assert hasattr(extractor, "extractItems")
    assert hasattr(extractor, "STANDARD_10K_ITEMS")


def test_extract_items_simple() -> None:
    """ITEM 패턴 매칭 + slice."""
    from dartlab.providers.edgar.docs.sections.extractor import extractItems

    html = "ITEM 1. Business\nBusiness text\nITEM 2. Properties\nProperty text"
    result = extractItems(html)
    assert "1" in result
    assert "2" in result


def test_item_label_lookup() -> None:
    """STANDARD_10K_ITEMS lookup."""
    from dartlab.providers.edgar.docs.sections.extractor import itemLabel

    assert itemLabel("1A") == "Risk Factors"
    assert itemLabel("7") == "MD&A"
