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

from .catalog import scenarioGuide
from .engine import compareScenarios, runScenario
from .presets import getScenario, listAllScenarios


def analyzeScenario(
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

    Parameters
    ----------
    name : str | None
        시나리오 이름. None이면 가이드 목록 반환.
    market : str
        시장 구분. ``"US"`` | ``"KR"``.
    severity : str | None
        심각도. ``"mild"`` / ``"moderate"`` / ``"severe"`` / ``"extreme"``.
    compare : bool
        ``True`` 이면 현재 baseline과 비교 delta 포함.
    **kwargs
        ``run_scenario`` 에 전달되는 추가 인자.

    Returns
    -------
    pl.DataFrame — name=None 일 때 (가이드 목록)
        name : str — 시나리오 이름
        category : str — 분류 (역사적 재현 / 유형별 / 한국 특화 등)
        type : str — 충격 유형 (신용 충격, 금리 충격 등)
        severity : str — 심각도 (mild/moderate/severe/extreme)
        description : str — 시나리오 설명

    dict — name 지정 시 (실행 결과)
        scenario : dict — 시나리오 적용 매크로 종합 결과
        baseline : dict | None — 현재 상태 (compare=True 일 때)
        delta : dict | None — 주요 지표 변화량 (compare=True 일 때)
        meta : dict — 시나리오 메타데이터 (name, description, type, severity 등)
    """
    if name is None:
        return scenarioGuide(market=market)

    return runScenario(name, severity=severity, market=market, compare=compare)


__all__ = [
    "analyze_scenario",
    "run_scenario",
    "compare_scenarios",
    "get_scenario",
    "list_all_scenarios",
    "scenario_guide",
]
