"""DartLab 컬러 팔레트 — 단일 원천 (viz SSOT).

Python 측 모든 시각화가 이 모듈에서 색상을 가져온다.
JS 측: `ui/shared/chart/colors.ts` (동일 값, 주석으로 교차 참조).

소비처 (web · jupyter · cli · blog · mcp) 는 catalog 의 `series.color` (hex)
또는 `series.intent` 를 자기 토큰으로 override 할 수 있다 — `render.*` 의
`paletteOverride` 인자 참조.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# Tailwind 500 saturate categorical 10 — modern SaaS 표준 (Vercel · Linear · Stripe).
# saturate 통일 (500 단계) + cool/warm 교차 배치 → 9 시리즈 stack 인접 hue 명확.
# 옛 muted earth (Tableau dusty / Anthropic warm) 가 dense stack 에서 인접 구분
# 부족 회귀 → saturate hue 분리로 전환. neutral 만 zinc (채도 0).
COLORS: list[str] = [
    "#0ea5e9",  # 0 sky-500       primary  cool
    "#f59e0b",  # 1 amber-500     accent   warm
    "#f43f5e",  # 2 rose-500      negative warm
    "#10b981",  # 3 emerald-500   positive cool
    "#8b5cf6",  # 4 violet-500    cool
    "#f97316",  # 5 orange-500    warm
    "#06b6d4",  # 6 cyan-500      cool
    "#d946ef",  # 7 fuchsia-500   warm
    "#84cc16",  # 8 lime-500      cool
    "#71717a",  # 9 zinc-500      neutral
]
"""Tailwind 500 saturate 10 — sky/amber/rose/emerald/violet/orange/cyan/fuchsia/lime/zinc."""


Intent = Literal["primary", "positive", "negative", "neutral", "accent"]
"""차트 시리즈의 *의미* 슬롯. 소비처가 자기 토큰으로 매핑할 때 lookup 키."""


# intent traffic-light 매핑 — Tailwind 표준 hue.
INTENT_MAP: dict[Intent, str] = {
    "primary": COLORS[0],  # sky     메인
    "positive": COLORS[3],  # emerald 긍정
    "negative": COLORS[2],  # rose    부정
    "accent": COLORS[1],  # amber   강조
    "neutral": COLORS[9],  # zinc    배경/참조
}
"""intent → 기본 hex 매핑."""


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
