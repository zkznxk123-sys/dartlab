"""View → ASCII/ANSI 차트 (cli/mcp).

renderers/ascii.py 의 renderAscii 가 옛 ChartSpec 포맷 입력 — 어댑터 거쳐 위임.
"""

from __future__ import annotations

from dartlab.viz.render.svg import _viewToLegacySpec
from dartlab.viz.schema import View


def toAscii(
    view: View,
    paletteOverride: dict[str, str] | None = None,
    *,
    width: int = 80,
    height: int = 20,
) -> str:
    """View → ASCII 차트 문자열. cli/mcp 출력.

    Args:
        view: builder.buildView 결과.
        paletteOverride: 어댑터 통일성을 위한 인자 (ASCII 는 색을 무시).
        width: ASCII 가로 문자 수.
        height: ASCII 세로 문자 수.

    Returns:
        멀티라인 ASCII/ANSI 문자열. plotext 우선, 없으면 fallback.
    """
    from dartlab.viz.renderers.ascii import renderAscii

    legacy = _viewToLegacySpec(view, paletteOverride)
    return renderAscii(legacy, width=width, height=height)


__all__ = ["toAscii"]
