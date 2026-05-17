"""DartLab 컬러 팔레트 — 단일 원천 (viz SSOT).

Python 측 모든 시각화가 이 모듈에서 색상을 가져온다.
JS 측: `ui/shared/chart/colors.ts` (동일 값, 주석으로 교차 참조).

소비처 (web · jupyter · cli · blog · mcp) 는 catalog 의 `series.color` (hex)
또는 `series.intent` 를 자기 토큰으로 override 할 수 있다 — `render.*` 의
`paletteOverride` 인자 참조.
"""

from __future__ import annotations

from typing import Literal, TypedDict

COLORS: list[str] = [
    "#ea4647",  # 0 primary red
    "#fb923c",  # 1 accent orange
    "#3b82f6",  # 2 blue
    "#22c55e",  # 3 green
    "#8b5cf6",  # 4 purple
    "#06b6d4",  # 5 cyan
    "#f59e0b",  # 6 amber
    "#ec4899",  # 7 pink
]
"""8 색 팔레트. 인덱스 순환: ``COLORS[i % len(COLORS)]``."""


Intent = Literal["primary", "positive", "negative", "neutral", "accent"]
"""차트 시리즈의 *의미* 슬롯. 소비처가 자기 토큰으로 매핑할 때 lookup 키."""


INTENT_MAP: dict[Intent, str] = {
    "primary": COLORS[2],  # blue
    "positive": COLORS[3],  # green
    "negative": COLORS[0],  # red
    "neutral": COLORS[4],  # purple
    "accent": COLORS[1],  # orange
}
"""intent → 기본 hex 매핑. `paletteOverride` 에 intent 키가 없으면 fallback."""


Tone = Literal["light", "dark"]


class ToneColors(TypedDict):
    """light/dark 톤별 비-시리즈 색상 (축선·그리드·배경·전경).

    catalog series.color 와 별개로 차트 프레임 (axis/grid) 의 톤을
    분리한다. 소비처는 자기 매체의 다크모드 토글에 따라 light 또는 dark
    의 ToneColors 를 골라 렌더러에 전달한다.
    """

    axis: str
    grid: str
    background: str
    foreground: str


TONE_MAP: dict[Tone, ToneColors] = {
    "light": {
        "axis": "#52525b",
        "grid": "#e4e4e7",
        "background": "#ffffff",
        "foreground": "#18181b",
    },
    "dark": {
        "axis": "#a1a1aa",
        "grid": "#3f3f46",
        "background": "#09090b",
        "foreground": "#fafafa",
    },
}
"""light/dark 톤 매핑. web 은 shadcn 토큰으로, jupyter 는 직접 lookup."""


def resolveColor(
    *,
    color: str | None = None,
    intent: Intent | None = None,
    key: str | None = None,
    override: dict[str, str] | None = None,
) -> str:
    """series.color 적용 우선순위.

    1. override[key]  — 가장 구체적 (시리즈 키별 강제 매핑)
    2. override[intent] — 의미 슬롯별 매핑
    3. color — catalog 기본 hex
    4. INTENT_MAP[intent] — intent 기본 hex
    5. COLORS[0] — 최종 fallback
    """
    if override:
        if key and key in override:
            return override[key]
        if intent and intent in override:
            return override[intent]
    if color:
        return color
    if intent:
        return INTENT_MAP.get(intent, COLORS[0])
    return COLORS[0]


__all__ = [
    "COLORS",
    "INTENT_MAP",
    "TONE_MAP",
    "Intent",
    "Tone",
    "ToneColors",
    "resolveColor",
]
