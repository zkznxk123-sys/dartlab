"""panel cross-engine 계약 (L0) — schema + period + canonicalKey + bridge. panel 의 spine.

gather build(disclosureKey 채움) 와 providers reader(fallback) 가 공유하는 단일 계약
SSOT. build(write)=gather / reader(read)=providers 가 본 계약만 의존해 서로 import 0
(filesystem + L0 계약으로 통신). network·lxml import 0 (L0 primitive).

panel 모듈 지도 (cross-layer — 본 L0 가 spine, R1 4계층 단방향):
    - L0 계약 (here)       ``core/panel/``                  schema · canonicalKey · period · bridge
    - L1 생산 (build)      ``gather/dart/panel/``           builder · walker · horizontalize · refScan · index · sync
    - L1 소비 (read)       ``providers/dart/panel/``        reader · anchor · pivot · cross · Panel facade
    - 수집 (fetch, online) ``providers/dart/openapi/``      DartClient · streamZipBytes (layer-밖 entry 가 build 와 조합)
  → 한 disclosure 가 canonical 정렬키가 되는 흐름: 본 ``canonicalKey`` (규칙) → build ``resolveBatch``
    (부착) → providers ``reader`` fallback. 정렬은 native ACLASS(정부 표준), 손 매핑 농장 없음.

공개표면 SSOT — caller 는 ``from dartlab.core.panel import X`` 만 (deep leaf import 금지):
    - 14-col ``PANEL_SCHEMA`` + ``PIVOT_INDEX`` (schema).
    - ``periodFromEnd`` / ``isPeriodColumn`` / ``sortPeriods`` (period 정규화 SSOT).
    - ``loadBridge`` / ``seedBridgeTier1`` (bridge 어휘 SSOT — US cross-market overlay).
    - ``canonicalKey`` / ``canonicalKeyExpr`` (native ACLASS scope-strip 정렬키 SSOT, KR within).
    - ``resolveDisclosureKey`` / ``resolveBatch`` / ``invalidateCache`` (canonical resolve).
"""

from __future__ import annotations

from .bridge import BRIDGE_SCHEMA, loadBridge, seedBridgeTier1, writeBridge
from .canonical import (
    canonicalKey,
    canonicalKeyExpr,
    invalidateCache,
    resolveBatch,
    resolveDisclosureKey,
)
from .period import isPeriodColumn, periodFromEnd, sortPeriods
from .schema import PANEL_SCHEMA, PIVOT_INDEX

__all__ = [
    "BRIDGE_SCHEMA",
    "PANEL_SCHEMA",
    "PIVOT_INDEX",
    "canonicalKey",
    "canonicalKeyExpr",
    "invalidateCache",
    "isPeriodColumn",
    "loadBridge",
    "periodFromEnd",
    "resolveBatch",
    "resolveDisclosureKey",
    "seedBridgeTier1",
    "sortPeriods",
    "writeBridge",
]
