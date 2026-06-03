"""EDGAR panel build (gather sections → cross-market 16-col 미러 artifact).

DART ``panel.build`` 의 EDGAR analog 이나 XML 파싱 0 — gather 가 이미 itemize 한 sections
(``data/edgar/sections/{ticker}/``)를 ``providers.dart.panel.schema.PANEL_SCHEMA`` 16-col flat
artifact (``data/edgar/panel/{ticker}.parquet``)로 컬럼 remap 한다. read 표면은 cross-market
``providers.dart.panel`` Panel/read (``marketNs="us"``) 를 무변경 재사용.

공개 표면:
    - ``buildEdgarPanel(ticker)`` — 1 ticker sections → panel artifact.
    - ``buildEdgarPanelAll(tickers)`` — 순차 fan-out (OOM 가드).
    - ``sectionsToPanel(long)`` — 순수 remap (테스트 가능).
    - ``parseTopic(topic)`` — topic → (form, itemId, sectionPath) 순수 규칙.
"""

from __future__ import annotations

from .builder import buildEdgarPanel, buildEdgarPanelAll, panelPath, sectionsToPanel
from .topicMap import itemIdExpr, parseTopic

__all__ = [
    "buildEdgarPanel",
    "buildEdgarPanelAll",
    "sectionsToPanel",
    "panelPath",
    "parseTopic",
    "itemIdExpr",
]
