"""viz/renderers — chartSpec → 매체 변환.

포함 예정 (Phase A.2 에서 채움):
- plotly.py — chart_from_spec (구 viz/plotly.py)
- svg.py — renderSvg (구 viz/svg.py)
- network.py — renderNetwork (구 viz/network.py)

ASCII 렌더는 viz/format/ascii.py 로 통합 (포맷이라 format/ 위치가 더 맞음).
viz/__init__.py 의 public re-export 가 동일 경로 (`from dartlab.viz import fromSpec`)
유지하도록 shim.
"""

from __future__ import annotations
