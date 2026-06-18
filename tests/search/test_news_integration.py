"""뉴스→검색 통합 단위 테스트 — _newsKey 네임스페이스, dartUrl source 분기, scope='news'.

search 모듈 내부 뉴스 통합(allFilings+panel+news 한 색인) 검증. 합성 입력으로 결정적.
"""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_news_key_namespace():
    """_newsKey 는 'news:' 접두 — DART 14자리 rcept_no 와 비충돌."""
    from dartlab.providers.dart.search.fieldIndexRebuild import _newsKey

    rn, so = _newsKey("https://news.example/article1", "2026-05-28")
    assert rn.startswith("news:")
    assert so == 0
    assert not rn[5:].isdigit() or len(rn) != 14  # 14자리 숫자 rcept_no 와 형태 분리
    # 동일 url → 동일 키 (결정적)
    assert _newsKey("https://news.example/article1", "x") == (rn, 0)


def test_resolve_result_url_branch():
    """dartUrl: 뉴스는 기사 url, 공시는 DART 뷰어 URL(rcpNo)."""
    from dartlab.providers.dart.search.fieldIndex import _resolveResultUrl

    df = pl.DataFrame(
        {
            "rcept_no": ["20260101000001", "news:abc123"],
            "source": ["allFilings", "news"],
            "url": ["", "https://n.example/a"],
        }
    )
    out = _resolveResultUrl(df)
    byUrl = {r["source"]: r["dartUrl"] for r in out.iter_rows(named=True)}
    assert byUrl["news"] == "https://n.example/a"
    assert "rcpNo=20260101000001" in byUrl["allFilings"]


def _newsRow(rcept, content, *, source, url="", report="", title="", stock="", corp_code=""):
    return {
        "rcept_no": rcept,
        "section_order": 0,
        "corp_code": corp_code,
        "corp_name": "",
        "stock_code": stock,
        "rcept_dt": "20260101",
        "report_nm": report,
        "section_title": title,
        "section_content": content,
        "source": source,
        "url": url,
    }


def test_search_scope_news(tmp_path, monkeypatch):
    """scope='news' 는 뉴스행만 반환, dartUrl=기사 url. corp 지정 시 0건(뉴스 corp 매핑 없음)."""
    import dartlab
    from dartlab.providers.dart.search import fieldIndex

    monkeypatch.setattr(fieldIndex, "_contentIndexDir", lambda: tmp_path)
    rows = [
        _newsRow(
            "20260101000001",
            "유상증자 결정 공시 본문",
            source="allFilings",
            report="유상증자",
            stock="005930",
            corp_code="00126380",
        ),
        _newsRow("news:x1", "유상증자 관련 속보 기사", source="news", url="https://n.example/a", title="google_news"),
    ]
    idx, meta = fieldIndex.buildContentSegment(rows, showProgress=False)
    fieldIndex.saveSegmentWithSidecar(idx, meta, "main", tmp_path)
    fieldIndex.clearCache()

    df = dartlab.search("유상증자", scope="news", limit=5)
    assert df.height >= 1
    assert set(df["source"].to_list()) == {"news"}
    assert df.row(0, named=True)["dartUrl"] == "https://n.example/a"

    # corp 지정 → 뉴스는 stock_code 빈값이라 0건
    df2 = dartlab.search("유상증자", scope="news", corp="005930", limit=5)
    assert df2.height == 0


def test_news_search_scope_registered():
    """SEARCH_SCOPES 에 'news' 등록 + 잘못된 scope ValueError."""
    import dartlab
    from dartlab.providers.dart.search import SEARCH_SCOPES

    assert "news" in SEARCH_SCOPES
    with pytest.raises(ValueError, match="scope"):
        dartlab.search("test", scope="invalid")
