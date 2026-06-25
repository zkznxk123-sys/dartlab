"""거시 패널 빌더 — gather 시리즈 → 월말 리샘플 → 정상성 변환.

데이터 SSOT = seriesFetch.getGather + g.macro(id)(forecast/regime 와 동일 경로, 별도빌드 0).
일간(금리·환율·원유)은 월말 last 리샘플, 공통 월로 정렬. logdiff100 변수는 누적 환산용
끝 레벨 보존. 불완전·표본부족은 None(simulate.py 가 fail-closed missing).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dartlab.macro.simulate._types import VarSpec


@dataclass(frozen=True)
class PanelData:
    """변환 패널 + 환산 메타."""

    panel: np.ndarray  # (T-1, n) 정상성 변환
    lastLevels: np.ndarray  # (n,) 끝 원시 레벨
    yms: list[str]  # 변환행 월 라벨(T-1)
    endYm: str


def _monthlySeries(g, seriesId: str) -> dict[str, float] | None:
    """시리즈 → {'YYYY-MM': 월말 last value}. 실패·빈값은 None."""
    import polars as pl

    try:
        df = g.macro(seriesId)
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    if df is None or len(df) == 0 or "date" not in df.columns or "value" not in df.columns:
        return None
    df = df.drop_nulls("value").sort("date")
    if len(df) == 0:
        return None
    df = df.with_columns(pl.col("date").dt.strftime("%Y-%m").alias("ym"))
    m = df.group_by("ym").agg(pl.col("value").last()).sort("ym")
    return dict(zip(m.get_column("ym").to_list(), m.get_column("value").to_list(), strict=True))


def buildPanel(g, specs: tuple[VarSpec, ...], minObs: int = 120) -> tuple[PanelData | None, list[dict]]:
    """시리즈 fetch → 완전 월패널 → 변환. 반환 (PanelData|None, missing[]).

    Args:
        g: gather 인스턴스(getGather).
        specs: 변수 사양.
        minObs: 변환 후 최소 관측(기본 120 ≈ 10년).

    Returns:
        (PanelData, []) 성공 / (None, [{id,status,reason}]) 실패(표본부족·시리즈부재).
    """
    maps: dict[str, dict[str, float] | None] = {s.seriesId: _monthlySeries(g, s.seriesId) for s in specs}
    missing = [
        {"id": sid, "status": "표시 보류", "reason": "시리즈 부재 또는 빈값"} for sid, v in maps.items() if v is None
    ]
    if missing:
        return None, missing

    common = sorted(set.intersection(*[set(v.keys()) for v in maps.values()]))  # type: ignore[union-attr]
    if len(common) < minObs + 1:
        return None, [
            {"id": "panel", "status": "표본 부족·표시 보류", "reason": f"공통월 {len(common)} < {minObs + 1}"}
        ]

    levels = np.array([[maps[s.seriesId][ym] for s in specs] for ym in common], dtype=float)  # type: ignore[index]
    t, n = levels.shape
    x = np.empty((t - 1, n))
    for i, s in enumerate(specs):
        if s.transform == "logdiff100":
            col = levels[:, i]
            if np.any(col <= 0):
                return None, [{"id": s.seriesId, "status": "표시 보류", "reason": "logdiff 비양수 값"}]
            x[:, i] = 100.0 * (np.log(col[1:]) - np.log(col[:-1]))
        else:
            x[:, i] = levels[1:, i]
    if not np.all(np.isfinite(x)):
        return None, [{"id": "panel", "status": "표시 보류", "reason": "변환 비유한값"}]
    return PanelData(x, levels[-1], common[1:], common[-1]), []
