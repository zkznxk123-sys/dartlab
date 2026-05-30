"""sections cross-engine 계약 (L0) — schema + bridge + disclosureKey resolve.

gather build(disclosureKey 채움) 와 providers reader(fallback) 가 공유하는 단일
계약 SSOT. build(write)=gather / reader(read)=providers 가 본 계약만 의존해
서로 import 0 (filesystem + L0 계약으로 통신).

공개:
    - 14-col ``SECTIONS_SCHEMA`` + ``PIVOT_INDEX`` (schema).
    - ``loadBridge`` / ``seedBridgeTier1`` (bridge SSOT).
    - ``resolveDisclosureKey`` / ``resolveBatch`` / ``invalidateCache`` (resolve).
"""

from __future__ import annotations

from .bridge import loadBridge, seedBridgeTier1
from .canonical import invalidateCache, resolveBatch, resolveDisclosureKey
from .schema import PIVOT_INDEX, SECTIONS_SCHEMA

__all__ = [
    "PIVOT_INDEX",
    "SECTIONS_SCHEMA",
    "invalidateCache",
    "loadBridge",
    "resolveBatch",
    "resolveDisclosureKey",
    "seedBridgeTier1",
]
