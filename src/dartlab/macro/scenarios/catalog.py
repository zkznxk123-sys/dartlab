"""시나리오 카탈로그 — 가이드 DataFrame."""

from __future__ import annotations

import polars as pl

from .presets import list_all_scenarios


def scenario_guide(market: str = "US") -> pl.DataFrame:
    """사용 가능한 시나리오 목록 DataFrame.

    ``dartlab.macro("시나리오")`` 무인자 호출 시 반환.

    Parameters
    ----------
    market : str
        시장 구분. ``"US"`` | ``"KR"``.

    Returns
    -------
    pl.DataFrame
        name : str — 시나리오 이름
        category : str — 분류 (역사적 재현 / 유형별 / 한국 특화 등)
        type : str — 충격 유형 (신용 충격, 금리 충격 등)
        severity : str — 심각도 (mild/moderate/severe/extreme)
        description : str — 시나리오 설명
    """
    items = list_all_scenarios(market=market)
    if not items:
        return pl.DataFrame(
            schema={"name": pl.Utf8, "category": pl.Utf8, "type": pl.Utf8, "severity": pl.Utf8, "description": pl.Utf8}
        )
    return pl.DataFrame(items)
