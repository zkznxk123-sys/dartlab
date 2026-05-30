"""panel read 표면 (L1 read, providers) — DART 공시 수평화 보드.

로컬 panel artifact(``data/dart/panel/{code}/{period}.parquet``) read only — network·lxml
import 0 (R2, BUILD=gather 와 물리 분리). 회사내(``Panel``)·회사간/세계마켓간(``crossCompany``/
``crossMarket``) 수평화 정규화.

공개표면 SSOT (deep leaf import 금지, R6):
    - ``Panel`` — 한 회사 수평화 보드 facade (board/show/wide/long/periods).
    - ``crossCompany`` / ``crossMarket`` — 다회사·다시장 동일 disclosure 정렬.
"""

from __future__ import annotations

from .cross import crossCompany, crossMarket
from .panel import Panel

__all__ = [
    "Panel",
    "crossCompany",
    "crossMarket",
]
