"""disclosure.py mirror test (P-PR7+8 skeleton)."""

import pytest

pytestmark = pytest.mark.unit


def test_imports() -> None:
    """모듈 import smoke."""
    from dartlab.providers.edgar import disclosure

    assert hasattr(disclosure, "parseForm4Xml")
    assert hasattr(disclosure, "parseDef14aHtml")
    assert hasattr(disclosure, "parseEightKHtml")
    assert hasattr(disclosure, "STANDARD_8K_ITEMS")


def test_parse_form4_xml_skeleton_empty() -> None:
    """form4 skeleton — 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import parseForm4Xml

    df = parseForm4Xml("")
    assert df.is_empty()
    assert "insider" in df.columns


def test_parse_def14a_html_skeleton_empty() -> None:
    """def14a skeleton — 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import parseDef14aHtml

    df = parseDef14aHtml("")
    assert df.is_empty()
    assert "name" in df.columns


def test_parse_eight_k_html_skeleton_empty() -> None:
    """eightK skeleton — 빈 DataFrame."""
    from dartlab.providers.edgar.disclosure import parseEightKHtml

    df = parseEightKHtml("")
    assert df.is_empty()


def test_item_label_lookup() -> None:
    """8-K STANDARD_8K_ITEMS lookup."""
    from dartlab.providers.edgar.disclosure import itemLabel

    assert itemLabel("2.02") == "Results of Operations and Financial Condition"
