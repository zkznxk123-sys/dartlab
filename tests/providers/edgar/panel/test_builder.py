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


def test_merge_keeping_schema_recasts_dtype_drift(tmp_path) -> None:
    """_mergeKeepingSchema — 옛 parquet 의 dtype drift 를 schema 계약으로 재캐스트 + 기존 보존."""
    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.edgar.panel.build.builder import _mergeKeepingSchema, _rowsToDf

    base = {k: None for k in PANEL_SCHEMA}
    old = {**base, "rceptNo": "OLD-1", "period": "2024Q4", "blockOrder": 5, "corp": "X"}
    # 기존 parquet 에 dtype drift 주입(blockOrder UInt32 → Int64)
    existing = _rowsToDf([old], PANEL_SCHEMA).with_columns(pl.col("blockOrder").cast(pl.Int64))
    target = tmp_path / "X.parquet"
    existing.write_parquet(str(target))

    new = {**base, "rceptNo": "NEW-1", "period": "2025Q1", "blockOrder": 7, "corp": "X"}
    merged = _mergeKeepingSchema(target, [new], PANEL_SCHEMA, {"NEW-1"})

    assert merged.schema == PANEL_SCHEMA  # drift 가 계약 dtype 으로 복구
    assert set(merged["rceptNo"].to_list()) == {"OLD-1", "NEW-1"}  # 기존 보존 + 신규


def test_merge_keeping_schema_prunes_with_empty_newrows(tmp_path) -> None:
    """newRows 가 비어도 ``accessions`` 의 기존 행은 제거 — board↔cell 정합(셀 0 정정 idempotent).

    회귀 가드(finding B): appendFilingsToPanel 이 셀 없는 공시(board only)에도 panelCell 을
    accessions 로 prune 해야 옛 셀이 남지 않는다. 그 prune 의 코어가 빈 newRows 처리다.
    """
    from dartlab.providers.edgar.panel.build.builder import _mergeKeepingSchema, _rowsToDf
    from dartlab.providers.edgar.panel.build.cellSchema import EDGAR_CELL_SCHEMA

    base = {k: None for k in EDGAR_CELL_SCHEMA}
    target = tmp_path / "cells.parquet"
    _rowsToDf([{**base, "rceptNo": "KEEP-1"}, {**base, "rceptNo": "DROP-1"}], EDGAR_CELL_SCHEMA).write_parquet(
        str(target)
    )

    merged = _mergeKeepingSchema(target, [], EDGAR_CELL_SCHEMA, {"DROP-1"})
    assert merged["rceptNo"].to_list() == ["KEEP-1"]  # newRows 비어도 DROP-1 prune


def test_merge_keeping_schema_warns_on_silent_cast_loss(tmp_path, caplog) -> None:
    """strict=False 재캐스트가 비-null 값을 *조용히* null 로 만들면(오버플로) 경고로 관측화(finding C)."""
    import logging

    from dartlab.providers.dart.panel.schema import PANEL_SCHEMA
    from dartlab.providers.edgar.panel.build.builder import _mergeKeepingSchema, _rowsToDf

    base = {k: None for k in PANEL_SCHEMA}
    # 기존 parquet 의 blockOrder(UInt32) 에 UInt32 max 초과 Int64 주입 → cast strict=False 시 null
    existing = _rowsToDf([{**base, "rceptNo": "OLD-1", "period": "2024Q4", "corp": "X"}], PANEL_SCHEMA).with_columns(
        pl.Series("blockOrder", [5_000_000_000], dtype=pl.Int64)
    )
    target = tmp_path / "X.parquet"
    existing.write_parquet(str(target))

    new = {**base, "rceptNo": "NEW-1", "period": "2025Q1", "blockOrder": 7, "corp": "X"}
    with caplog.at_level(logging.WARNING):
        merged = _mergeKeepingSchema(target, [new], PANEL_SCHEMA, {"NEW-1"})

    assert merged.filter(pl.col("rceptNo") == "OLD-1")["blockOrder"].to_list() == [None]  # 오버플로 → null
    assert any("비-null→null" in r.message for r in caplog.records)  # 손실 경고 남김


def test_build_edgar_panel_all(builtTicker) -> None:
    """buildEdgarPanelAll — 명시 ticker list + None(원본 docs dir 전수 cik→ticker 역해소)."""
    from dartlab.providers.edgar.panel.build.builder import buildEdgarPanelAll

    res = buildEdgarPanelAll(["TEST"])
    assert res["TEST"]["rows"] > 0 and res["TEST"]["cells"] > 0
    # None → data/original/edgar/docs/ 전수 (TEST 의 cik 폴더 역해소)
    resAll = buildEdgarPanelAll(None)
    assert "TEST" in resAll and resAll["TEST"]["rows"] > 0
