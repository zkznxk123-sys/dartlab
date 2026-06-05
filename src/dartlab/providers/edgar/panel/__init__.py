"""EDGAR panel (공시 수평화) — DART panel mirror, 단일 artifact (marketNs="us").

DART panel 의 단일 panel 저장 원칙을 EDGAR 에 적용:
- **보드** (16-col ``PANEL_SCHEMA``) — 재무제표를 presentation role→정규 statement key(BS/IS/CF/CIS/EF)로
  disclosureKey 앵커링, 서술 Item 은 narrative. ``Panel(ticker)`` / ``c.panel`` (US 기본,
  ``data/edgar/panel/{ticker}.parquet``).
- **native 재무** — fact/context/role 결합 결과를 같은 panel row ``contentRaw`` payload 로 보존.
  소문자 ``Panel(ticker)("is")`` / ``c.panel("is")`` 는 이 payload 를 read-time 분해한다.

**build** (``build/``)는 SEC full-submission text 를 저장하지 않고 메모리에서 **자급 파싱** —
submission(SGML)→linkbase(EX-101.PRE/LAB)→walker(보드)+native payload. sections/gather/meta 의존 0.
별도 ``panelCell`` artifact 는 없다.

공개표면 (deep leaf import 금지, R6):
    - ``Panel`` (``Panel(ticker)``) — 보드 read, 기본 ``marketNs="us"``.
    - ``compare`` — DART compare 와 같은 회사간 panel 비교 표면.
    - ``read``/``schema``/``period``/``mapper``/``canonical``/``spine`` — DART panel 과 같은 뼈대 이름.
    - ``build`` subpackage — ``buildEdgarPanel(ticker, filings)`` (운영자/CI artifact 생산).
"""

from .compare import compare
from .panel import Panel

__all__ = ["Panel", "compare"]
