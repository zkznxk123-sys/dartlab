"""Product search result schema contract tests."""

from __future__ import annotations

import json

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def _patchIndexDir(monkeypatch, tmp_path):
    from dartlab.providers.dart.search import fieldIndex

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda tier=None: tmp_path)
    return fieldIndex


def _buildMain(fieldIndex, tmp_path, rows):
    idx, meta = fieldIndex.buildContentSegment(rows, showProgress=False)
    fieldIndex.saveSegmentWithSidecar(idx, meta, "main", tmp_path)
    fieldIndex.clearCache()


def _row(
    rcept: str,
    content: str,
    *,
    source: str = "allFilings",
    section: int = 0,
    date: str = "20260615",
    url: str = "",
) -> dict:
    return {
        "rcept_no": rcept,
        "section_order": section,
        "corp_code": "00126380",
        "corp_name": "삼성전자",
        "stock_code": "005930",
        "rcept_dt": date,
        "report_nm": "주요사항보고서",
        "section_title": "자금조달",
        "section_content": content,
        "source": source,
        "sourceDataAsOf": date,
        "url": url,
    }


def test_content_search_result_has_product_schema(tmp_path, monkeypatch):
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("20260615000001", "유상증자 자금조달 목적 운영자금", section=2)],
    )

    df = fieldIndex.searchContent("유상증자", limit=5)
    top = df.row(0, named=True)
    assert top["source"] == "allFilings"
    assert top["sourceRef"] == "dart:allFilings:20260615000001#section=2"
    assert top["dataAsOf"] == "20260615"
    assert top["answerable"] is True
    assert top["notAnswerableReason"] == ""
    assert "유상증자" in top["snippet"]
    cards = json.loads(top["fieldCards"])
    assert cards
    assert any(card["label"] == "sourceRef" for card in cards)
    assert any(card.get("evidence") and "유상증자" in card["evidence"] for card in cards)


def test_unified_search_preserves_product_schema(tmp_path, monkeypatch):
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("news:abc123", "반도체 수출 뉴스 속보", source="news", url="https://n.example/a")],
    )

    from dartlab.providers.dart.search.unified import searchUnified

    df = searchUnified("반도체 뉴스", limit=5)
    top = df.row(0, named=True)
    assert top["source"] == "news"
    assert top["sourceRef"] == "news:abc123"
    assert top["dartUrl"] == "https://n.example/a"
    assert top["answerable"] is True


def test_public_search_both_restores_product_schema_after_concat(tmp_path, monkeypatch):
    import polars as pl

    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("20260615000002", "대표이사 변경 이사회 결의", section=1)],
    )
    from dartlab.providers.dart.search import api as searchApi

    monkeypatch.setattr(searchApi, "_searchTitle", lambda *args, **kwargs: pl.DataFrame())

    df = searchApi.search("대표이사 변경", scope="both", limit=5)
    assert df.height >= 1
    for col in ("source", "sourceRef", "dataAsOf", "snippet", "answerable", "fieldCards"):
        assert col in df.columns
    assert df.row(0, named=True)["sourceRef"].startswith("dart:")


def test_memory_card_set_uses_answerable_source_refs(tmp_path, monkeypatch):
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("20260615000003", "전환사채 발행 자금조달", section=3)],
    )

    df = fieldIndex.searchContent("전환사채", limit=5)
    from dartlab.providers.dart.search.memoryCard import buildMemoryCardSet

    memory = buildMemoryCardSet(df, query="전환사채 자금조달", limit=2)
    assert memory["sourceRefs"] == ["dart:allFilings:20260615000003#section=3"]
    assert memory["dataAsOfBySource"] == {"allFilings": "20260615"}
    assert memory["cards"][0]["fieldCards"]


def test_public_search_adds_query_focused_chunk_evidence(tmp_path, monkeypatch):
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("20260615000004", "앞내용 " * 20 + "전환사채 발행 목적 운영자금 " + "뒤내용 " * 20, section=4)],
    )

    from dartlab.providers.dart.search import api as searchApi

    df = searchApi.search("전환사채", scope="content", limit=5)
    cards = json.loads(df.row(0, named=True)["fieldCards"])
    chunkCards = [card for card in cards if card["label"] == "chunk"]
    assert chunkCards
    assert "전환사채" in chunkCards[0]["evidence"]


def test_public_search_adds_entity_graph_cards_when_catalog_exists(tmp_path, monkeypatch):
    fieldIndex = _patchIndexDir(monkeypatch, tmp_path)
    _buildMain(
        fieldIndex,
        tmp_path,
        [_row("20260615000005", "반도체 HBM 투자 후공정", section=5, date="20260616")],
    )
    catalogPath = tmp_path / "entityGraphCatalog.parquet"
    pl.DataFrame(
        [
            {
                "stockCode": "005930",
                "corpName": "삼성전자",
                "grade": "dCR-AAA",
                "weakAxis": "사업안정성",
                "stageName": "전공정(FAB)",
                "chainName": "반도체",
                "dataAsOf": "20260616",
                "neighborsJson": json.dumps(
                    [
                        {
                            "stockCode": "000660",
                            "corpName": "SK하이닉스",
                            "grade": "dCR-AA",
                            "weakAxis": "현금흐름",
                            "stageName": "전공정(FAB)",
                        }
                    ],
                    ensure_ascii=False,
                ),
            }
        ]
    ).write_parquet(catalogPath)
    monkeypatch.setenv("DARTLAB_SEARCH_ENTITY_GRAPH_CATALOG", str(catalogPath))

    from dartlab.providers.dart.search import api as searchApi
    from dartlab.providers.dart.search import entityGraph

    entityGraph._CATALOG_CACHE.clear()
    df = searchApi.search("반도체 HBM 투자", scope="content", limit=5)
    row = df.row(0, named=True)
    entityCards = json.loads(row["entityCards"])

    assert row["entityResolved"] is True
    assert row["entityStockCode"] == "005930"
    assert any(card["label"] == "peer:SK하이닉스" for card in entityCards)
