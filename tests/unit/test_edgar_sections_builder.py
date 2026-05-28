"""EDGAR sectionsBuilder + itemBoundary 가드 — PR-E2 plan delegated-prancing-tower.

본 PR-E2 단독 검증:
- itemBoundary.splitTextTable 의 markdown text/table 분리 정확성
- itemBoundary.sanitizeRawHtml 의 script/style/ix:* 제거 + table ALIGN 보존
- itemBoundary.extractItemChunks 의 row schema (2 column + meta)
- sectionsBuilder.emitPeriodArtifacts 의 period-shard 양식 + atomic write
- sectionsBuilder.emitIndexArtifact 의 _index.parquet 양식

HF 네트워크 의존 없이 in-process synthetic filing 데이터로 검증.
"""

from __future__ import annotations

import polars as pl
import pytest

from dartlab.providers.edgar.docs.sections.itemBoundary import (
    extractItemChunks,
    sanitizeRawHtml,
    splitTextTable,
)
from dartlab.providers.edgar.docs.sections.sectionsBuilder import (
    buildSectionRowsFromFiling,
    emitIndexArtifact,
    emitPeriodArtifacts,
    removeSectionsArtifact,
)
from dartlab.providers.edgar.docs.sections.sectionsStorage import (
    hasSectionsArtifact,
    indexPath,
    listAvailablePeriods,
    loadSectionsIndex,
    sectionsPath,
)

_FIXTURE_TICKER = "TEST_AAPL_FIXTURE"


@pytest.fixture(autouse=True)
def _cleanupFixture():
    """각 테스트 전/후 fixture ticker artifact 청소."""
    removeSectionsArtifact(_FIXTURE_TICKER)
    yield
    removeSectionsArtifact(_FIXTURE_TICKER)


def test_split_text_table_basic() -> None:
    """markdown text/table 분리."""
    content = "Some paragraph.\nAnother line.\n| col1 | col2 |\n| --- | --- |\n| a | b |"
    text, table = splitTextTable(content)
    assert text == "Some paragraph.\nAnother line."
    assert "| col1 | col2 |" in table
    assert "| --- | --- |" in table


def test_split_text_table_no_table() -> None:
    """표 없는 content 는 table 부분이 빈 string."""
    text, table = splitTextTable("only paragraph here.")
    assert text == "only paragraph here."
    assert table == ""


def test_split_text_table_only_table() -> None:
    """본문 없는 표 only — text 부분이 빈 string."""
    text, table = splitTextTable("| a | b |\n| --- | --- |\n| 1 | 2 |")
    assert text == ""
    assert "| a | b |" in table


def test_sanitize_raw_html_removes_noise() -> None:
    """script/style/header/footer/nav 제거 + table ALIGN 보존."""
    html = """
    <html><body>
    <script>alert('x')</script>
    <style>p {color:red}</style>
    <header>Site Header</header>
    <p>Real content</p>
    <table>
      <tr><td align="right">100</td><td align="left">a</td></tr>
    </table>
    <footer>Site Footer</footer>
    </body></html>
    """
    out = sanitizeRawHtml(html)
    assert "<script" not in out.lower()
    assert "<style" not in out.lower()
    assert "<header" not in out.lower()
    assert "<footer" not in out.lower()
    assert "Real content" in out
    # ALIGN 속성 보존 (viewer 시각 fidelity 핵심).
    assert 'align="right"' in out.lower()
    assert "<table" in out.lower()


def test_extract_item_chunks_schema() -> None:
    """extractItemChunks 결과의 row schema — content_raw + content_plain + meta."""
    items = [
        {
            "title": "Item 1. Business",
            "content": "Apple designs products.\n| metric | value |\n| --- | --- |\n| revenue | 100 |",
        },
        {"title": "Item 1A. Risk Factors", "content": "Various risks."},
    ]
    meta = {
        "ticker": "AAPL",
        "cik": "0000320193",
        "accession_no": "0000320193-24-000123",
        "filing_date": "2024-11-01",
        "form_type": "10-K",
        "period_key": "2024Q4",
        "filing_url": "https://example.com",
        "year": 2024,
    }
    rows = extractItemChunks(items, "<html><body><p>Business</p></body></html>", "10-K", meta)
    assert rows, "extractItemChunks 결과 비어있음"
    # 모든 row 가 공통 schema 보유.
    for r in rows:
        assert "topic" in r
        assert "blockType" in r
        assert "content_raw" in r
        assert "content_plain" in r
        assert "accession_no" in r
        assert r["accession_no"] == "0000320193-24-000123"
        assert r["ticker"] == "AAPL"
    # 첫 item 은 text + table 분리되어 최소 2 row (text + table 1 개 이상).
    item1Rows = [r for r in rows if r["topic"].endswith("Business")]
    blockTypes = {r["blockType"] for r in item1Rows}
    assert "text" in blockTypes
    assert "table" in blockTypes


def test_extract_item_chunks_shares_content_raw() -> None:
    """모든 row 가 filing-level content_raw 를 공유 (parquet dict encoding 최적화)."""
    items = [
        {"title": "Item 1. Business", "content": "Para 1."},
        {"title": "Item 1A. Risk Factors", "content": "Para 2."},
    ]
    meta = {"ticker": "AAPL", "cik": "0000320193", "accession_no": "x", "form_type": "10-K", "period_key": "2024Q4"}
    rows = extractItemChunks(items, "<html><body>SHARED_HTML_BODY</body></html>", "10-K", meta)
    rawValues = {r["content_raw"] for r in rows}
    assert len(rawValues) == 1, "모든 row 의 content_raw 가 filing-level 공유 필요"


def test_build_section_rows_from_filing_sets_period() -> None:
    """buildSectionRowsFromFiling 가 period 컬럼을 meta.period_key 로 설정."""
    items = [{"title": "Item 1. Business", "content": "Para"}]
    meta = {
        "ticker": "AAPL",
        "cik": "0000320193",
        "accession_no": "x",
        "form_type": "10-K",
        "period_key": "2024Q4",
        "year": 2024,
    }
    rows = buildSectionRowsFromFiling(
        items=items,
        rawHtml="<html><body><p>x</p></body></html>",
        formType="10-K",
        meta=meta,
    )
    assert rows
    for r in rows:
        assert r["period"] == "2024Q4"


def test_emit_period_artifacts_writes_per_period() -> None:
    """emitPeriodArtifacts 가 period 별 parquet 파일 생성."""
    meta = {
        "ticker": _FIXTURE_TICKER,
        "cik": "0000000000",
        "accession_no": "acc1",
        "form_type": "10-K",
        "period_key": "2024Q4",
        "year": 2024,
    }
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P"}],
        rawHtml="<html><body><p>X</p></body></html>",
        formType="10-K",
        meta=meta,
    )
    # 두 번째 period 도.
    meta2 = dict(meta)
    meta2["accession_no"] = "acc2"
    meta2["period_key"] = "2024Q3"
    rows += buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P2"}],
        rawHtml="<html><body><p>Y</p></body></html>",
        formType="10-K",
        meta=meta2,
    )
    result = emitPeriodArtifacts(_FIXTURE_TICKER, rows)
    assert result["periodsWritten"] == 2
    assert result["totalRows"] == len(rows)
    assert sectionsPath(_FIXTURE_TICKER, "2024Q4").exists()
    assert sectionsPath(_FIXTURE_TICKER, "2024Q3").exists()
    assert hasSectionsArtifact(_FIXTURE_TICKER)
    assert set(listAvailablePeriods(_FIXTURE_TICKER)) >= {"2024Q4", "2024Q3"}


def test_emit_index_artifact_dedup() -> None:
    """emitIndexArtifact 의 accession_no dedup — amendment 처리."""
    filings = [
        {
            "accession_no": "a1",
            "period_key": "2024Q4",
            "filing_date": "2024-11-01",
            "form_type": "10-K",
            "filing_url": "u1",
            "cik": "c",
        },
        {
            "accession_no": "a2",
            "period_key": "2024Q3",
            "filing_date": "2024-08-01",
            "form_type": "10-Q",
            "filing_url": "u2",
            "cik": "c",
        },
        # 중복 accession (amendment) — last keep.
        {
            "accession_no": "a1",
            "period_key": "2024Q4",
            "filing_date": "2024-12-01",
            "form_type": "10-K/A",
            "filing_url": "u3",
            "cik": "c",
        },
    ]
    # 디렉터리 미생성 시 emit 가능하도록 미리 한 row 빌드 (period parquet 1 개 생성).
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P"}],
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
    path = emitIndexArtifact(_FIXTURE_TICKER, filings)
    assert path is not None and path == indexPath(_FIXTURE_TICKER)
    idx = loadSectionsIndex(_FIXTURE_TICKER)
    assert idx is not None
    # accession_no a1 의 마지막 (10-K/A) 만 남아야.
    a1Rows = idx.filter(pl.col("accession_no") == "a1")
    assert a1Rows.height == 1
    assert a1Rows["form_type"][0] == "10-K/A"


def test_remove_sections_artifact() -> None:
    """removeSectionsArtifact 가 디렉터리 통째 삭제."""
    meta = {
        "ticker": _FIXTURE_TICKER,
        "cik": "c",
        "accession_no": "a",
        "form_type": "10-K",
        "period_key": "2024Q4",
        "year": 2024,
    }
    rows = buildSectionRowsFromFiling(
        items=[{"title": "Item 1. Business", "content": "P"}],
        rawHtml="<p>x</p>",
        formType="10-K",
        meta=meta,
    )
    emitPeriodArtifacts(_FIXTURE_TICKER, rows)
    assert hasSectionsArtifact(_FIXTURE_TICKER)
    n = removeSectionsArtifact(_FIXTURE_TICKER)
    assert n > 0
    assert not hasSectionsArtifact(_FIXTURE_TICKER)
