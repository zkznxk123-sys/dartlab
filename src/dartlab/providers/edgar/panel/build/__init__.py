"""EDGAR panel build — SEC full-submission text → 16-col panel 단일 artifact.

호출자가 fetch 한 full-submission text 를 자급 파싱(sections/gather/meta 의존 0):
submission(SGML) → linkbase(EX-101.PRE/LAB) → walker(보드, 재무표 disclosureKey 앵커링)
+ native payload. 원문 `.txt` 저장과 별도 panelCell artifact 는 없다.

공개 표면:
    - ``buildEdgarPanel(ticker, filings)`` / ``buildEdgarPanelAll({ticker: filings})`` — artifact 생산.
    - ``appendFilingTextsToPanel(ticker, filings)`` — per-filing 증분 append.
    - ``filingTextToBoard(txt, *, ticker)`` — 1 필링 → 보드 rows.
    - ``panelPath(ticker)`` — artifact 경로.
"""

from __future__ import annotations

from .builder import (
    appendFilingTextsToPanel,
    buildEdgarPanel,
    buildEdgarPanelAll,
    existingAccessions,
    filingTextToBoard,
    panelPath,
    resolveCikForTicker,
)

__all__ = [
    "appendFilingTextsToPanel",
    "buildEdgarPanel",
    "buildEdgarPanelAll",
    "existingAccessions",
    "filingTextToBoard",
    "panelPath",
    "resolveCikForTicker",
]
