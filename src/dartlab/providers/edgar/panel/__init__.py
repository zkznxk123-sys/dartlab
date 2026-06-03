"""EDGAR panel (공시 수평화) — DART-panel급 XBRL 보드 + 셀 (raw `.txt` 자급 파싱, marketNs="us").

DART panel 의 2층을 필링 inline us-gaap XBRL 로 재현:
- **보드** (16-col ``PANEL_SCHEMA``) — 재무제표를 presentation role→정규 statement key(BS/IS/CF/CIS/EF)로
  disclosureKey 앵커링, 서술 Item 은 narrative. ``Panel(ticker, marketNs="us")`` / ``c.panel`` (DART read
  표면 재사용, ``data/edgar/panel/{ticker}.parquet``).
- **native 셀** (``EDGAR_CELL_SCHEMA``) — 필링 inline(ix:)/INS(native) XBRL fact×context×role 분해 →
  계정×기간. ``c.panel("is"/"bs"/"cf"/"cis"/"sce"/"ratios")`` (``cellRead``, ``data/edgar/panelCell/{ticker}
  .parquet``) = DART native(소문자) 대칭. 대문자 ``c.panel("IS")`` = companyfacts(finance facade) 대칭.

**build** (``build/``)는 gather 원본 ``data/original/edgar/docs/{cik}/*.txt`` (SEC full-submission)를
**자급 파싱** — submission(SGML)→instance(facts+context)→linkbase(EX-101.PRE/LAB)→walker(보드)+cell(셀).
sections/gather/meta 의존 0(폐기-무관), 전 history. DART buildPanel(zip 파싱)의 EDGAR 미러.

공개표면 (deep leaf import 금지, R6):
    - ``Panel`` (``Panel(ticker, marketNs="us")``) — 보드 read (DART 표면 재사용).
    - ``cellRead`` — native 셀 read (``readNative``; c.panel 소문자 위임, facade _nativeFn 주입).
    - ``build`` subpackage — ``buildEdgarPanel(ticker)`` (운영자/CI artifact 생산).
"""

from dartlab.providers.dart.panel import Panel

__all__ = ["Panel"]
