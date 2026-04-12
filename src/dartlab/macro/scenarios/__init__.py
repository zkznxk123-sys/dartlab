"""매크로 시나리오 시뮬레이션 — 6막의 "앞으로 어떻게 되나".

110개 프리셋: 역사적 충격 15개 + Fed DFAST 3개 + 유형별 24개
+ 현대적 리스크 24개 + 구조적 20개 + 한국 특화 24개

Usage::

    import dartlab

    dartlab.macro("시나리오")                          # 가이드
    dartlab.macro("시나리오", "2008 금융위기")          # 역사적 재현
    dartlab.macro("시나리오", "신용 충격", severity="severe")
"""

from __future__ import annotations

import polars as pl

from .catalog import scenario_guide
from .engine import compare_scenarios, run_scenario
from .presets import get_scenario, list_all_scenarios


def analyze_scenario(
    name: str | None = None,
    *,
    market: str = "US",
    severity: str | None = None,
    compare: bool = True,
    **kwargs,
) -> pl.DataFrame | dict:
    """시나리오 분석 — 축 계약 준수.

    macro("시나리오")                          → 가이드 (110개 목록)
    macro("시나리오", "2008 금융위기")          → 실행 + baseline 비교
    macro("시나리오", "신용 충격", severity="severe") → 심각도 지정

    Args:
        name: 시나리오 이름. None이면 가이드.
        market: "US" | "KR"
        severity: 심각도 (mild/moderate/severe/extreme)
        compare: True면 현재 baseline과 비교

    Returns:
        name=None: 시나리오 목록 DataFrame
        name 지정: 시나리오 실행 결과 dict
    """
    if name is None:
        return scenario_guide(market=market)

    return run_scenario(name, severity=severity, market=market, compare=compare)


__all__ = [
    "analyze_scenario",
    "run_scenario",
    "compare_scenarios",
    "get_scenario",
    "list_all_scenarios",
    "scenario_guide",
]
