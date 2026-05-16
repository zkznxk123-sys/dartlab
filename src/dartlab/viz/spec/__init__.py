"""ChartSpec 어휘 — VizSpec 데이터클래스 + ref helper + extract + intents.

- chartSpec.py — VizSpec 데이터클래스 (`from dartlab.viz.spec import VizSpec`)
- refs.py — evidence ref helper (tableRef · valueRef · filingDeepLink · chartEvidenceBinding · seriesPointRefs)
- extract.py — stdout 마커 추출 (extractVizSpecs)
- intents.py — viz intent catalog (VIZ_INTENTS · VizIntent · listVizIntents)
"""

from __future__ import annotations

from dartlab.viz.spec.chartSpec import VizSpec

__all__ = ["VizSpec"]
