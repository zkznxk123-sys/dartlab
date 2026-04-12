"""시나리오 카탈로그 — 가이드 DataFrame."""

from __future__ import annotations

import polars as pl

from .presets import list_all_scenarios


def scenario_guide(market: str = "US") -> pl.DataFrame:
    """사용 가능한 시나리오 목록 DataFrame.

    dartlab.macro.scenario() 무인자 호출 시 반환.
    """
    items = list_all_scenarios(market=market)
    if not items:
        return pl.DataFrame(
            schema={"name": pl.Utf8, "category": pl.Utf8, "type": pl.Utf8, "severity": pl.Utf8, "description": pl.Utf8}
        )
    return pl.DataFrame(items)
