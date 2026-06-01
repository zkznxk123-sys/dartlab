"""panel read 표면 (L1 read, providers) — DART 공시 수평화 보드.

로컬 panel artifact(``data/dart/panel/{code}/{period}.parquet``) read only — network·lxml
import 0 (R2, BUILD=gather 와 물리 분리). 한 회사 공시를 항목 × period 보드로 수평화.

공개표면 SSOT (deep leaf import 금지, R6):
    - ``Panel`` — 한 회사 수평화 wide (``pl.DataFrame`` subclass) + ``__call__`` 섹션 검색.
"""

from __future__ import annotations

from .panel import Panel

__all__ = [
    "Panel",
]
