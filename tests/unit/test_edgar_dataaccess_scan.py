"""EDGAR D.1 진입점 가드 — PR-E6 plan delegated-prancing-tower.

본 PR-E6 단독 검증:
- ``_looksLikeEdgarTicker`` 판별 — 영문 ticker True, KR 6 자리 False
- ``_loadEdgarSectionsAsDocs`` 가 EDGAR sections artifact → 옛 docs schema 변환
- ``loadDocsForStock(ticker)`` 가 ticker 입력 시 EDGAR path 사용
- 호환 schema (year/section_title/section_content/period) 노출 — caller 변경 0

artifact 부재 시 None — caller (sentiment/risk 등) 가 None 분기.
"""

from __future__ import annotations

from dartlab.providers.edgar.docs.sections.sectionsBuilder import (
    buildSectionRowsFromFiling,
    emitPeriodArtifacts,
    removeSectionsArtifact,
)
from dartlab.quant.screen._dataAccessScan import (
    _loadEdgarSectionsAsDocs,
    _looksLikeEdgarTicker,
    loadDocsForStock,
)

_FIXTURE_TICKER = "ZTSTA"  # SEC ticker 양식 (영문 1~5 자) — underscore 미허용.


def test_looks_like_edgar_ticker_yes() -> None:
    """영문 ticker → True."""
    assert _looksLikeEdgarTicker("AAPL")
    assert _looksLikeEdgarTicker("MSFT")
    assert _looksLikeEdgarTicker("BRK.B")
    assert _looksLikeEdgarTicker("BRK-B")


def test_looks_like_edgar_ticker_no_for_kr() -> None:
    """6 자리 KR stockCode → False (DART path 유지)."""
    assert not _looksLikeEdgarTicker("005930")
    assert not _looksLikeEdgarTicker("000660")
    assert not _looksLikeEdgarTicker("123456")
    assert not _looksLikeEdgarTicker("")


def test_loads_edgar_sections_as_docs_returns_none_when_absent() -> None:
    """artifact 부재 ticker → None."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    import os

    os.environ["DARTLAB_NO_HF_DOWNLOAD"] = "1"
    try:
        assert _loadEdgarSectionsAsDocs(_FIXTURE_TICKER) is None
    finally:
        os.environ.pop("DARTLAB_NO_HF_DOWNLOAD", None)


def test_loads_edgar_sections_as_docs_exposes_compat_schema() -> None:
    """artifact 있을 때 year / section_title / section_content 컬럼 노출 (caller 변경 0)."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "Apple designs products."}],
        rawHtml="<p>x</p>",
        formType="10-K",
        meta={
            "ticker": _FIXTURE_TICKER,
            "cik": "c",
            "accession_no": "a1",
            "form_type": "10-K",
            "period_key": "2024Q4",
            "year": 2024,
        },
    )
    emitPeriodArtifacts(_FIXTURE_TICKER, rows)
    try:
        df = _loadEdgarSectionsAsDocs(_FIXTURE_TICKER)
        assert df is not None
        assert "year" in df.columns
        assert "section_title" in df.columns
        assert "section_content" in df.columns
        # year = "2024" prefix (period_key "2024Q4" 의 4 자리).
        years = df["year"].unique().to_list()
        assert "2024" in years
        # section_content 가 markdown 본문 (옛 docs.parquet section_content 와 의미 동일).
        content = df["section_content"][0]
        assert isinstance(content, str)
        assert "Apple designs products" in content
    finally:
        removeSectionsArtifact(_FIXTURE_TICKER)


def test_load_docs_for_stock_dispatches_to_edgar_for_ticker() -> None:
    """loadDocsForStock(ticker) 가 EDGAR path 사용 — DART path 도달 0 보장."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 7. MDA", "content": "MD&A body."}],
        rawHtml="<p>x</p>",
        formType="10-K",
        meta={
            "ticker": _FIXTURE_TICKER,
            "cik": "c",
            "accession_no": "a1",
            "form_type": "10-K",
            "period_key": "2024Q4",
            "year": 2024,
        },
    )
    emitPeriodArtifacts(_FIXTURE_TICKER, rows)
    try:
        df = loadDocsForStock(_FIXTURE_TICKER)
        assert df is not None
        assert "section_content" in df.columns
        # EDGAR path 가 부재 분기 안 탔는지 — content 가 EDGAR markdown 본문.
        content = df["section_content"][0]
        assert "MD&A" in content or "body" in content
    finally:
        removeSectionsArtifact(_FIXTURE_TICKER)


def test_load_docs_for_stock_kr_path_unaffected() -> None:
    """KR 6 자리 stockCode 는 DART path 그대로 (EDGAR 분기 안 함).

    artifact 부재 KR 종목 → log warning + None 반환 (옛 동작 동일).
    """
    df = loadDocsForStock("999999")  # 부재 KR 종목
    # 옛 path 가 None 반환 (artifact 없음 + docs.parquet 없음).
    assert df is None
