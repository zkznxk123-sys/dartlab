"""viz/render — View → 매체별 출력 4 매체.

각 매체 함수의 시그니처: `to{Medium}(view, paletteOverride?) → 매체 결과`.

paletteOverride 우선순위: series.key > series.intent > series.color (catalog 기본).
미지정 시 series.color 그대로.
"""

from __future__ import annotations

from dartlab.viz.render.ascii import toAscii
from dartlab.viz.render.plotly import toPlotly
from dartlab.viz.render.recharts import toRechartsSpec
from dartlab.viz.render.svg import toSvg

__all__ = ["toAscii", "toPlotly", "toRechartsSpec", "toSvg"]
