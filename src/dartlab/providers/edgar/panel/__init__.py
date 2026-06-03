"""EDGAR panel (공시 수평화) — cross-market read 표면 재사용 + EDGAR build (marketNs="us").

**read 표면**은 ``providers.dart.panel`` 의 ``Panel`` 을 그대로 재사용한다 (``PANEL_SCHEMA`` 16-col
cross-market 계약, 값만 us-gaap — schema.py 가 명시 endorse). ``Panel(ticker, marketNs="us")`` 로
``data/edgar/panel/{ticker}.parquet`` 를 wide 수평화. read.py/mapper.py/canonical/ 복제 0(DRY).

**build** (``build/``)는 EDGAR 전용 — gather 가 이미 itemize 한 sections
(``data/edgar/sections/{ticker}/``)를 16-col flat artifact 로 컬럼 remap (XML 파싱 0). DART
build(walker/refScan/dechunkNotes) 와 달리 gather 가 추출 완료라 remap 만.

공개표면 (deep leaf import 금지, R6):
    - ``Panel`` (``Panel(ticker, marketNs="us")``) — 한 회사 공시 수평화 보드 (read).
    - ``build`` subpackage — ``buildEdgarPanel(ticker)`` 등 (운영자/CI artifact 생산).
"""

from dartlab.providers.dart.panel import Panel

__all__ = ["Panel"]
