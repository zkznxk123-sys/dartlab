"""panel cross-engine 계약 (L0) — schema + period + bridge + disclosureKey resolve.

gather build(disclosureKey 채움) 와 providers reader(fallback) 가 공유하는 단일 계약
SSOT. build(write)=gather / reader(read)=providers 가 본 계약만 의존해 서로 import 0
(filesystem + L0 계약으로 통신). network·lxml import 0 (L0 primitive).

공개표면 SSOT — caller 는 ``from dartlab.core.panel import X`` 만 (deep leaf import 금지):
    - 14-col ``PANEL_SCHEMA`` + ``PIVOT_INDEX`` (schema).
    - ``periodFromEnd`` / ``isPeriodColumn`` / ``sortPeriods`` (period 정규화 SSOT).
    - ``loadBridge`` / ``seedBridgeTier1`` (bridge 어휘 SSOT).
    - ``resolveDisclosureKey`` / ``resolveBatch`` / ``invalidateCache`` (canonical resolve).
"""

from __future__ import annotations

from .bridge import loadBridge, seedBridgeTier1
from .canonical import invalidateCache, resolveBatch, resolveDisclosureKey
from .period import isPeriodColumn, periodFromEnd, sortPeriods
from .schema import PANEL_SCHEMA, PIVOT_INDEX

__all__ = [
    "PANEL_SCHEMA",
    "PIVOT_INDEX",
    "invalidateCache",
    "isPeriodColumn",
    "loadBridge",
    "periodFromEnd",
    "resolveBatch",
    "resolveDisclosureKey",
    "seedBridgeTier1",
    "sortPeriods",
]
