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
    """시나리오 분석 단일 진입점 — 가이드 목록 또는 실행 + baseline 비교.

    Capabilities:
        매크로 시나리오 110 개 (역사적 재현 15 + Fed DFAST 3 + 유형별 24 + 현대적 리스크 24
        + 구조적 20 + 한국 특화 24) 의 두 모드 진입점. `name=None` 이면 가이드 DataFrame,
        `name` 지정 시 시나리오 실행 + 현재 baseline 과의 delta 비교.

    Parameters
    ----------
    name : str | None, default None
        시나리오 이름. None 이면 110 개 가이드 목록 반환.
    market : str, default "US"
        시장 코드 — "US" | "KR".
    severity : str | None, default None
        심각도 — "mild" | "moderate" | "severe" | "extreme". 유형별/현대 리스크 시나리오에 적용.
    compare : bool, default True
        True 면 현재 baseline 과 비교 delta 포함.
    **kwargs
        runScenario 전달 인자.

    Returns
    -------
    pl.DataFrame | dict
        DataFrame (name=None) : name/category/type/severity/description 컬럼
        dict (name 지정) : scenario/baseline/delta/meta

    Raises
    ------
    없음 (시나리오 이름 미일치 시 빈 dict).

    Example
    -------
    >>> import dartlab
    >>> dartlab.macro("시나리오")
    <pl.DataFrame 110 rows>
    >>> dartlab.macro("시나리오", "2008 금융위기")
    {'scenario': {...}, 'baseline': {...}, 'delta': {...}, 'meta': {...}}

    Guide
    -----
    동일 충격 유형 (신용/금리/환율 등) 의 강도별 비교에는 severity 4 단계 인자 사용. compare=False
    면 baseline fetch 비용 절약 (대량 시나리오 일괄 실행 시 권장).

    SeeAlso
    -------
    - ``dartlab.macro.scenarios.engine.runScenario`` : 단일 시나리오 실행
    - ``dartlab.macro.scenarios.engine.compareScenarios`` : 다 시나리오 비교
    - ``dartlab.macro.scenarios.catalog.scenarioGuide`` : 가이드 목록

    Requires
    --------
    - L1 gather: 매크로 baseline (compare=True 일 때)
    - L1.5 synth: scenario 매핑

    AIContext
    ---------
    "이 시나리오가 오면" 질문의 1 차 진입. delta 의 주요 필드 (예: equity, credit) 만 인용해도
    한 단락 답변 가능. severity 미지정 시 default "moderate" 가정.
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
