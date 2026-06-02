"""의미검색(scope=auto) gated fusion 단위 테스트 — 경험확장 회수 + graceful degrade + panel 소스.

실험 V237 recipe(bm25 + type→본문 경험확장 + gated fusion)의 본진 이식 검증. 합성 fixture 로 결정적.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _patchIndexDir(monkeypatch, tmp_path):
    """fieldIndex·semantic 양쪽의 _contentIndexDir 를 tmp 로 — 출력·아티팩트 격리."""
    from dartlab.providers.dart.search import fieldIndex, semantic

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda: tmp_path)
    monkeypatch.setattr(semantic, "_contentIndexDir", lambda: tmp_path)
    return fieldIndex, semantic


def _buildSegment(fieldIndex, tmp_path, rows):
    idx, meta = fieldIndex.buildContentSegment(rows, showProgress=False)
    fieldIndex.saveSegment(idx, meta, "main", outDir=tmp_path)
    fieldIndex.clearCache()


def _row(rcept, content, *, source="allFilings", report="공시", title=""):
    return {
        "rcept_no": rcept,
        "section_order": 0,
        "corp_code": "00000000",
        "corp_name": "테스트",
        "stock_code": "000000",
        "rcept_dt": "20260101",
        "report_nm": report,
        "section_title": title,
        "section_content": content,
        "source": source,
    }


def test_graceful_degrade_without_meaning(tmp_path, monkeypatch):
    """meaning.json 부재 → searchSemantic 은 bm25 단독으로 동작 (크래시 없음)."""
    fieldIndex, semantic = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000001", "매출 증가와 영업이익 개선"),
            _row("20260101000002", "유상증자 결정 공시"),
        ],
    )
    df = semantic.searchSemantic("매출", limit=5)
    assert df is not None
    assert "info" not in df.columns
    assert df.height >= 1
    assert "20260101000001" in df["rcept_no"].to_list()


def test_meaning_expansion_recovers_synonym(tmp_path, monkeypatch):
    """meaning.json 의 경험확장이 키워드 없는 동의 문서를 회수 (gated fusion)."""
    fieldIndex, semantic = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000010", "외상매출금 회수 정책 안내"),  # 질의어 직접 포함 (bm25 hit)
            _row("20260101000011", "매출채권 및 채권 평가 손실 인식"),  # 질의어 없음, 동의 'channel' 통해서만
            _row("20260101000012", "유상증자 신주 발행 가액"),  # 무관
        ],
    )
    # 경험그래프: 질의 '외상매출금' → 본문 '채권' 으로 확장
    graph = {"tok:외상매출금": {"채권": 8.0}, "tok:매출채권": {"채권": 8.0}}
    (tmp_path / "meaning.json").write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    # bm25 단독(scope=content): 질의어 직접 포함 문서만
    from dartlab.providers.dart.search.fieldIndex import searchContent

    bmHits = set(searchContent("외상매출금", limit=5)["rcept_no"].to_list())
    assert "20260101000011" not in bmHits  # 키워드로는 동의 문서 못 잡음

    # 의미검색: 경험확장으로 동의 문서(...011) 회수
    df = semantic.searchSemantic("외상매출금", limit=5)
    hits = set(df["rcept_no"].to_list())
    assert "20260101000011" in hits  # 의미가 키워드 사각을 메움


def test_panel_source_searchable(tmp_path, monkeypatch):
    """source='panel' 롤업 문서도 검색된다 (allFilings·panel 통합 색인)."""
    fieldIndex, semantic = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000020", "재고자산 평가 및 매출원가", source="panel", title="재고자산"),
            _row("20260101000021", "현금흐름표 영업활동", source="allFilings"),
        ],
    )
    df = semantic.searchSemantic("재고자산", limit=5)
    assert df.height >= 1
    top = df.row(0, named=True)
    assert top["rcept_no"] == "20260101000020"
    assert top["source"] == "panel"
