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


def test_build_edgar_panel_all(builtTicker) -> None:
    """buildEdgarPanelAll — 명시 ticker list + None(원본 docs dir 전수 cik→ticker 역해소)."""
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanelAll

    res = buildEdgarPanelAll(["TEST"])
    assert res["TEST"]["rows"] > 0 and res["TEST"]["cells"] > 0
    # None → data/original/edgar/docs/ 전수 (TEST 의 cik 폴더 역해소)
    resAll = buildEdgarPanelAll(None)
    assert "TEST" in resAll and resAll["TEST"]["rows"] > 0
