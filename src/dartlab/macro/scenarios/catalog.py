"""시나리오 카탈로그 — 가이드 DataFrame."""

from __future__ import annotations

import polars as pl

from .presets import listAllScenarios


def scenarioGuide(market: str = "US") -> pl.DataFrame:
    """사용 가능한 시나리오 목록 DataFrame.

    Capabilities:
        listAllScenarios 결과를 polars DataFrame 으로 포맷팅 — 매크로 시나리오
        카탈로그의 UI/CLI 진입점.

    Args:
        market: ``"US"`` | ``"KR"``.

    Returns:
        pl.DataFrame (컬럼: name/category/type/severity/description).

    Example:
        >>> df = scenarioGuide("US")
        >>> df.columns
        ['name', 'category', 'type', 'severity', 'description']

    Guide:
        ``dartlab.macro("시나리오")`` 무인자 호출 시 본 함수 결과. 사용자에게
        카탈로그 노출 후 name 으로 runScenario.

    When:
        Macro engine "시나리오" 키 무인자 호출 + AI 시나리오 카탈로그 답변.

    How:
        listAllScenarios → DataFrame 변환 (빈 결과면 빈 스키마 DataFrame).

    Requires:
        없음 (정적 카탈로그).

    Raises:
        없음.

    See Also:
        - listAllScenarios : list 형태 결과
        - runScenario : 단일 실행

    AIContext:
        DataFrame head 3~5 행 + 전체 row 수 인용으로 카탈로그 노출.

    LLM Specifications:
        AntiPatterns:
            - DataFrame 전체 dump (행 수 다수)
            - category group_by 누락한 채 dump
        OutputSchema:
            polars DataFrame ``(name, category, type, severity, description)``.
        Prerequisites: 없음.
        Freshness: 정적.
        Dataflow: listAllScenarios → DataFrame.
        TargetMarkets: US, KR.
    """
    items = listAllScenarios(market=market)
    if not items:
        return pl.DataFrame(
            schema={"name": pl.Utf8, "category": pl.Utf8, "type": pl.Utf8, "severity": pl.Utf8, "description": pl.Utf8}
        )
    return pl.DataFrame(items)
