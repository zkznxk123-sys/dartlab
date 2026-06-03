"""EDGAR panel build — raw SEC `.txt` 직접 파싱 → 16-col 보드 + EDGAR_CELL 셀 (자급, DART 미러).

gather 원본 ``data/original/edgar/docs/{cik}/{accession}.txt`` 를 자급 파싱(sections/gather/meta 의존 0):
submission(SGML) → instance(inline facts+context) → linkbase(EX-101.PRE/LAB) → walker(보드, 재무표
disclosureKey 앵커링) + cell(계정×기간 셀). read 표면은 ``providers.dart.panel`` (marketNs="us") 재사용.

공개 표면:
    - ``buildEdgarPanel(ticker)`` / ``buildEdgarPanelAll(tickers)`` — artifact 생산 (운영자/CI).
    - ``filingToBoardAndCells(txtPath, *, ticker)`` — 1 필링 → (보드 rows, 셀 rows) (순수, 테스트).
    - ``panelPath(ticker)`` / ``panelCellPath(ticker)`` — artifact 경로.
"""

from __future__ import annotations

from .builder import (
    buildEdgarPanel,
    buildEdgarPanelAll,
    filingToBoardAndCells,
    panelCellPath,
    panelPath,
    resolveCikForTicker,
)

__all__ = [
    "buildEdgarPanel",
    "buildEdgarPanelAll",
    "filingToBoardAndCells",
    "panelPath",
    "panelCellPath",
    "resolveCikForTicker",
]
