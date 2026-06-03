"""EDGAR panel read 표면 round-trip — build → Panel(marketNs="us") wide·callable·search (합성 데이터).

synthetic sections → ``buildEdgarPanel`` → cross-market ``Panel(ticker, marketNs="us")`` read.
tmp dataDir 격리(monkeypatch) + ``DARTLAB_NO_HF_DOWNLOAD`` 로 network 0. read 표면이 EDGAR 16-col
artifact 를 wide 수평화하고 callable 섹션검색·search 가 동작함을 검증 (cross-market 재사용 증명).
"""

from __future__ import annotations

import polars as pl
import pytest

import dartlab.config as _config

pytestmark = pytest.mark.unit


def _writeSyntheticSections(dataDir, ticker: str) -> None:
    """tmp dataDir 에 합성 sections artifact (2 period) 작성 — gather 산출 형태."""
    base = dataDir / "edgar" / "sections" / ticker.upper()
    base.mkdir(parents=True, exist_ok=True)
    for period, accn, biz in [("2024Q4", "0000320193-24-1", "biz 2024"), ("2023Q4", "0000320193-23-9", "biz 2023")]:
        pl.DataFrame(
            {
                "topic": ["10-K::item1Business", "10-K::item1ARiskFactors"],
                "blockType": ["text", "table"],
                "blockOrder": [0, 1],
                "source_title": ["Item 1. Business", "Item 1A. Risk Factors"],
                "content_raw": [f"<p>{biz}</p>", "<table>supply chain risk</table>"],
                "content_plain": [biz, "supply chain risk"],
                "period": [period, period],
                "ticker": [ticker.upper(), ticker.upper()],
                "accession_no": [accn, accn],
                "form_type": ["10-K", "10-K"],
            }
        ).write_parquet(str(base / f"{period}.parquet"))


@pytest.fixture
def _builtPanel(tmp_path, monkeypatch):
    """tmp dataDir 격리 → 합성 sections → buildEdgarPanel → ticker 반환."""
    monkeypatch.setattr(_config, "dataDir", str(tmp_path))
    monkeypatch.setenv("DARTLAB_NO_HF_DOWNLOAD", "1")
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel

    _writeSyntheticSections(tmp_path, "TESTX")
    stats = buildEdgarPanel("TESTX")
    assert stats["rows"] == 4 and stats["periods"] == 2, stats
    return "TESTX"


def test_panel_us_wide_round_trip(_builtPanel) -> None:
    """Panel(ticker, marketNs="us") → wide pl.DataFrame (item × period 수평화)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_builtPanel, marketNs="us")
    assert isinstance(p, pl.DataFrame)
    assert not p.is_empty()
    for col in ("chapter", "sectionLeaf", "blockLeaf", "disclosureKey", "scope"):
        assert col in p.columns, f"식별 컬럼 부재: {col}"
    # period 열 — 최신 좌측 (2024Q4, 2023Q4 둘 다 존재)
    assert "2024Q4" in p.columns and "2023Q4" in p.columns
    # item1Business 가 두 기간에 같은 행으로 수평화 (1 행, 두 period 열 채워짐)
    bizRows = p.filter(pl.col("sectionLeaf") == "item1Business")
    assert bizRows.height == 1, "item1Business 가 기간 간 한 행으로 수평화 안 됨"


def test_panel_us_callable_section_search(_builtPanel) -> None:
    """callable 섹션 검색 — sectionLeaf(itemId) + blockLeaf(source_title) substring 매칭."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_builtPanel, marketNs="us")
    # blockLeaf "Item 1A. Risk Factors" substring
    risk = p("Risk")
    assert risk is not None and risk.height >= 1
    # sectionLeaf itemId exact-ish
    biz = p("item1Business")
    assert biz is not None and biz.height == 1


def test_panel_us_full_text_search(_builtPanel) -> None:
    """search(term) — 본문(period 셀) 전체검색."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_builtPanel, marketNs="us")
    hits = p.search("supply chain")
    assert hits is not None and hits.height >= 1


def test_panel_us_scope_consolidated(_builtPanel) -> None:
    """EDGAR(xbrlClass null) → scope 전부 'consolidated' (연결-only, scopeExpr graceful)."""
    from dartlab.providers.dart.panel import Panel

    p = Panel(_builtPanel, marketNs="us")
    assert set(p["scope"].unique()) == {"consolidated"}
