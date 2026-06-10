"""통합 검색 R*(scope=auto) 단위 테스트 — 큐레이션·라우팅 확장 회수 + always-safe + graceful degrade.

unifiedSearchRecipe 확정 레시피(plain BM25 ⊕ 확장 BM25 RRF)의 본진 이식 검증. 합성 fixture 로 결정적.
"""

from __future__ import annotations

import json

import pytest

pytestmark = pytest.mark.unit


def _patchIndexDir(monkeypatch, tmp_path):
    """fieldIndex._contentIndexDir 를 tmp 로 — 세그먼트·router.json 격리."""
    from dartlab.providers.dart.search import fieldIndex, unified

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda: tmp_path)
    return fieldIndex, unified


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


def test_plain_exact_term_without_artifacts(tmp_path, monkeypatch):
    """router.json 부재 + 동의어 미발화 → plain BM25 단독으로 동작 (크래시 없음)."""
    fieldIndex, unified = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000001", "매출 증가와 영업이익 개선"),
            _row("20260101000002", "유상증자 결정 공시"),
        ],
    )
    df = unified.searchUnified("영업이익", limit=5)
    assert df is not None
    assert "info" not in df.columns
    assert df.row(0, named=True)["rcept_no"] == "20260101000001"


def test_curated_synonym_recovers_informal(tmp_path, monkeypatch):
    """구어 질의("자사주")가 큐레이션 동의어(자기주식)로 키워드 사각 문서를 회수."""
    fieldIndex, unified = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000010", "자기주식 취득 결정 보통주 100만주"),  # '자사주' 표면형 없음
            _row("20260101000011", "유상증자 신주 발행 가액 확정"),  # 무관
        ],
    )
    df = unified.searchUnified("자사주 샀다", limit=5)
    hits = df["rcept_no"].to_list()
    assert "20260101000010" in hits  # 동의어 확장이 사각을 메움
    assert df.row(0, named=True)["rcept_no"] == "20260101000010"


def test_router_canon_lane(tmp_path, monkeypatch):
    """router.json 라우팅 canon 이 표면형 0 인 자유구어 질의를 회수 (always-safe RRF)."""
    fieldIndex, unified = _patchIndexDir(monkeypatch, tmp_path)
    from dartlab.providers.dart.search.router import buildRouterModel

    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000020", "현금배당 결정 주당 500원 지급"),
            _row("20260101000021", "공급계약 체결 반도체 장비 납품"),
        ],
    )
    model = buildRouterModel(
        {
            "dividend": {
                "router": ["주주한테 돈 나눠주기로 했어?", "주주 환원 현금 지급", "돈 나눠주는 회사"],
                "canon": ["배당", "현금배당"],
            },
            "supplyContract": {
                "router": ["수주 따냈다", "납품 계약 체결", "큰 계약 맺은 곳"],
                "canon": ["공급계약", "납품"],
            },
        }
    )
    (tmp_path / "router.json").write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")

    df = unified.searchUnified("주주한테 돈 나눠준대", limit=5)
    hits = df["rcept_no"].to_list()
    assert "20260101000020" in hits  # canon(배당·현금배당) lane 이 회수
    assert df.row(0, named=True)["rcept_no"] == "20260101000020"


def test_edgar_panel_rollup_indexed(tmp_path, monkeypatch):
    """EDGAR panel(동일 16-col 스키마)이 filing 롤업으로 색인 — source='edgar-panel', dartUrl 빈값."""
    import polars as pl

    from dartlab.providers.dart.search import fieldIndex, fieldIndexRebuild, unified

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda tier=None: tmp_path)
    edgarDir = tmp_path / "edgarPanel"
    edgarDir.mkdir()
    pl.DataFrame(
        {
            "rceptNo": ["0001090872-15-000032", "0001090872-15-000032"],
            "period": ["2015Q1", "2015Q1"],
            "contentRaw": ["<p>revenue increased due to semiconductor demand</p>", "<p>risk factors include</p>"],
            "sectionLeaf": ["10-Q", "10-Q"],
        }
    ).write_parquet(edgarDir / "AAPL.parquet")
    monkeypatch.setattr(fieldIndexRebuild, "_edgarPanelDir", lambda: edgarDir)

    n = fieldIndexRebuild.rebuildMain(
        includeAllFilings=False, includePanel=False, includeEdgarPanel=True, showProgress=False
    )
    assert n == 1  # rceptNo 롤업 = 1 filing 1 문서
    fieldIndex.clearCache()
    df = unified.searchUnified("semiconductor revenue", limit=5)
    top = df.row(0, named=True)
    assert top["rcept_no"] == "0001090872-15-000032"
    assert top["source"] == "edgar-panel"
    assert top["report_nm"] == "10-Q"
    assert top["dartUrl"] == ""  # accession 은 DART 뷰어 URL 조합 불가 — 빈값(정직)


def test_expansion_preserves_plain_top(tmp_path, monkeypatch):
    """확장이 발화해도 plain lane 1 위(정확 매칭)가 RRF 상위에 보존된다 (always-safe)."""
    fieldIndex, unified = _patchIndexDir(monkeypatch, tmp_path)
    _buildSegment(
        fieldIndex,
        tmp_path,
        [
            _row("20260101000030", "배당 배당금 현금배당 결정"),  # 질의 직접 매칭 최강
            _row("20260101000031", "배당성향 안내"),  # 동의어로만 걸림
        ],
    )
    df = unified.searchUnified("배당", limit=5)  # '배당' 은 큐레이션 키 → 확장 발화
    assert df.row(0, named=True)["rcept_no"] == "20260101000030"
