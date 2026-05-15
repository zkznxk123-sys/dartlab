"""viz/core — viz 전 sub-module 이 공유하는 저수준.

포함 예정 (Phase A.2~A.6 에서 점진 채움):
- spec.py (VizSpec) — 구 viz/spec.py 에서 이동
- refs.py (tableRef/valueRef/filingDeepLink/chartEvidenceBinding/seriesPointRefs) — 구 viz/refs.py
- extract.py (extractVizSpecs) — 구 viz/extract.py
- emit.py (emitChart/emitDiagram) — 구 viz/__init__.py 의 emit 함수
- palette.py — dartlab.core.palette thin re-export
- chartKind.py — Literal kind enum (line/bar/area/pie/barH/kpi/table/waterfall)
- formatting.py — 숫자/통화/날짜 포맷 helper

이 module 은 dartlab.viz 의 가장 안쪽 계층. 순환 import 위험 0 (leaf modules only).
"""

from __future__ import annotations
