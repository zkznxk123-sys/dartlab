"""EDGAR panel topicMap mirror — parseTopic(scalar) ↔ itemIdExpr(Expr) 동치 (데이터 0).

``providers/edgar/panel/build/topicMap.py`` 의 형식 규칙 검증. 첫 ``::`` 기준 분리, ``::`` 부재
honest passthrough, scalar/Expr 동치 (DART canonicalKey/canonicalKeyExpr 쌍 패턴).
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_parse_topic_form_item_path() -> None:
    """topic → (form, itemId, sectionPath) 첫 ``::`` 분리."""
    from dartlab.providers.edgar.panel.build.topicMap import parseTopic

    assert parseTopic("10-K::item1Business") == ("10-K", "item1Business", "10-K::item1Business")
    assert parseTopic("10-Q::partIItem2Mdna") == ("10-Q", "partIItem2Mdna", "10-Q::partIItem2Mdna")


def test_parse_topic_no_separator_passthrough() -> None:
    """``::`` 부재 시 (topic, topic, topic) honest passthrough."""
    from dartlab.providers.edgar.panel.build.topicMap import parseTopic

    assert parseTopic("bare") == ("bare", "bare", "bare")
    assert parseTopic("") == ("", "", "")
    assert parseTopic(None) == ("", "", "")


def test_parse_topic_first_separator_wins() -> None:
    """다중 ``::`` 는 첫 구분자 기준 — itemId 가 나머지 전체."""
    from dartlab.providers.edgar.panel.build.topicMap import parseTopic

    assert parseTopic("a::b::c") == ("a", "b::c", "a::b::c")


def test_item_id_expr_matches_scalar() -> None:
    """itemIdExpr(Expr) == parseTopic[1](scalar) — 동일 규칙 (분기 0)."""
    from dartlab.providers.edgar.panel.build.topicMap import itemIdExpr, parseTopic

    topics = ["10-K::item1Business", "10-Q::partIItem1ARiskFactors", "bare", "a::b::c", ""]
    df = pl.DataFrame({"topic": topics})
    exprOut = df.select(itemIdExpr())["sectionLeaf"].to_list()
    scalarOut = [parseTopic(t)[1] for t in topics]
    assert exprOut == scalarOut, f"Expr/scalar 불일치: {exprOut} != {scalarOut}"
