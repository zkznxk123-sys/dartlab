"""EDGAR panel builder — 합성 원본 `.txt` → 보드(16-col) + 셀(EDGAR_CELL) 통합 (data 0)."""

from __future__ import annotations

import polars as pl
import pytest

pytestmark = pytest.mark.unit


def test_filing_to_board_and_cells(builtTicker) -> None:
    from pathlib import Path

    import dartlab.config as cfg
    from dartlab.providers.edgar.panel.build.builder import filingToBoardAndCells

    txt = Path(cfg.dataDir) / "original" / "edgar" / "docs" / "0000012345" / "0000012345-25-000001.txt"
    board, cells = filingToBoardAndCells(txt, ticker=builtTicker)
    assert board and cells
    # 재무표 disclosureKey 앵커 (BS/IS 본표)
    anchored = {r["disclosureKey"] for r in board if r["disclosureKey"]}
    assert "BS" in anchored and "IS" in anchored
    # 서술 leaf 는 null key
    assert any(r["disclosureKey"] is None and r["leafType"] == "text" for r in board)


def test_build_edgar_panel_artifacts(builtTicker) -> None:
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanel, panelCellPath, panelPath
    from dartlab.providers.edgar.panel.build.cellSchema import EDGAR_CELL_SCHEMA

    stats = buildEdgarPanel(builtTicker)
    assert stats["rows"] > 0 and stats["cells"] > 0 and stats["filings"] == 1

    board = pl.read_parquet(str(panelPath(builtTicker)))
    assert list(board.columns) == list(PANEL_SCHEMA.keys()), "보드 16-col 계약 위반"
    assert board.schema == PANEL_SCHEMA
    assert board["period"].unique().to_list() == ["2024Q4"]
    assert board.filter(pl.col("corp") == "TEST").height == board.height

    cellp = panelCellPath(builtTicker)
    assert cellp.exists()
    cells = pl.read_parquet(str(cellp))
    assert list(cells.columns) == list(EDGAR_CELL_SCHEMA.keys()), "셀 14-col 계약 위반"
    assert set(cells["statement"].unique().to_list()) <= {"BS", "IS", "CF", "CIS", "EF"}


def test_resolve_cik(builtTicker) -> None:
    from dartlab.providers.edgar.panel.build.builder import resolveCikForTicker

    assert resolveCikForTicker("TEST") == "0000012345"
    assert resolveCikForTicker("test") == "0000012345"  # 대소문자 무관
    assert resolveCikForTicker("NOPE") is None


def test_append_filings_to_panel_incremental(builtTicker, tmp_path) -> None:
    """appendFilingsToPanel — 신규 accession 만 기존 artifact 에 append + 정정 idempotent.

    회귀 가드: per-filing 증분이 전체 history 재독 없이 동작하고, 같은 accession 재-append 가
    행을 늘리지 않아야(중복 0) EDGAR raw 폐기 전략과 정합.
    """
    from pathlib import Path

    import dartlab.config as cfg
    from dartlab.providers.edgar.panel.build.builder import (
        appendFilingsToPanel,
        buildEdgarPanel,
        existingAccessions,
        panelPath,
    )

    from .synthData import synthSubmissionTxt

    # 초기 빌드 (1 filing)
    buildEdgarPanel(builtTicker, overwrite=True)
    acc0 = existingAccessions(builtTicker)
    rows0 = pl.read_parquet(str(panelPath(builtTicker))).height
    assert len(acc0) == 1 and rows0 > 0

    # 신규 filing(다른 accession + period) append
    docsDir = Path(cfg.dataDir) / "original" / "edgar" / "docs" / "0000012345"
    p2 = docsDir / "0000012345-25-000002.txt"
    p2.write_text(synthSubmissionTxt(accession="0000012345-25-000002", periodEnd="20231231"), encoding="utf-8")
    stat = appendFilingsToPanel(builtTicker, [p2])
    assert stat["appended"] == 1
    acc1 = existingAccessions(builtTicker)
    rows1 = pl.read_parquet(str(panelPath(builtTicker))).height
    assert len(acc1) == 2 and rows1 > rows0  # 기존 보존 + 신규 추가

    # 같은 accession 재-append → 행 불변(정정 idempotent, 중복 0)
    appendFilingsToPanel(builtTicker, [p2])
    rows2 = pl.read_parquet(str(panelPath(builtTicker))).height
    assert rows2 == rows1


def test_list_recent_filings_parse() -> None:
    """listRecentFilings — master.idx 파싱(form 필터·accession·txt_url) — 네트워크 mock."""
    from dartlab.gather.original.edgar import collect

    idx = (
        "Description: Master Index\n"
        "CIK|Company Name|Form Type|Date Filed|Filename\n"
        "--------------------------------------------------------\n"
        "320193|APPLE INC|10-Q|2026-06-03|edgar/data/320193/0000320193-26-000077.txt\n"
        "1234|FOO CORP|8-K|2026-06-03|edgar/data/1234/0001234-26-000001.txt\n"
    )

    class _Resp:
        status_code = 200
        text = idx

        def raise_for_status(self):
            return None

    import httpx

    orig = httpx.get
    httpx.get = lambda *a, **k: _Resp()  # noqa: E731
    try:
        rows = collect.listRecentFilings(["20260603"], forms=["10-Q", "10-K"])
    finally:
        httpx.get = orig

    assert len(rows) == 1  # 8-K 제외
    r = rows[0]
    assert r["cik"] == "0000320193" and r["accession_no"] == "0000320193-26-000077"
    assert r["txt_url"].endswith("edgar/data/320193/0000320193-26-000077.txt")


def test_build_edgar_panel_all(builtTicker) -> None:
    """buildEdgarPanelAll — 명시 ticker list + None(원본 docs dir 전수 cik→ticker 역해소)."""
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanelAll

    res = buildEdgarPanelAll(["TEST"])
    assert res["TEST"]["rows"] > 0 and res["TEST"]["cells"] > 0
    # None → data/original/edgar/docs/ 전수 (TEST 의 cik 폴더 역해소)
    resAll = buildEdgarPanelAll(None)
    assert "TEST" in resAll and resAll["TEST"]["rows"] > 0
