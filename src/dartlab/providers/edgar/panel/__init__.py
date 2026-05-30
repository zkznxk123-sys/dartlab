"""EDGAR panel (공시 수평화) read 표면 — market-neutral reader 재사용 (marketNs="us").

panel reader 는 시장 무관 설계(G7) — 동일 14-col PANEL_SCHEMA·disclosureKey 계약이라
``providers.dart.panel`` 의 ``Panel`` / ``crossCompany`` / ``crossMarket`` 을 그대로 재사용한다
(reader 무변경 보장). EDGAR 호출은 marketNs="us" — artifact 경로가 ``data/edgar/panel`` 로
분기된다. EDGAR panel artifact 의 BUILD(gather, us-gaap walker)는 후속 — 본 read 표면은
이미 준비됨.

공개표면 (deep leaf import 금지, R6):
    - ``Panel`` (``Panel(cik, marketNs="us")``) — 한 회사 공시 수평화 보드.
    - ``crossCompany`` / ``crossMarket`` — 회사간·세계마켓간 정렬 (DART↔EDGAR).
"""

from __future__ import annotations

from dartlab.providers.dart.panel import Panel, crossCompany, crossMarket

__all__ = ["Panel", "crossCompany", "crossMarket"]
