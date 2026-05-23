"""SEC iXBRL fact 시계열 horizontalize — concept × period DataFrame.

dart/parse/tableHorizontalizer 의 SEC 등가. iXBRL fact (long format) 을
horizontalized (wide) DataFrame 으로 pivot — caller 가 시계열 분석 시 직관.

본 wrapper 는 thin — context 정보 (period start/end) 활용은 별 cycle.
"""

from __future__ import annotations

import polars as pl


def horizontalizeFacts(facts: pl.DataFrame, *, periodCol: str = "contextRef") -> pl.DataFrame:
    """iXBRL fact (long) → concept × period (wide) DataFrame.

    Args:
        facts: ``extractIxbrlFacts`` 결과 — ``concept`` / ``value`` /
            ``contextRef`` 컬럼 보유.
        periodCol: period 식별 컬럼명 (default ``"contextRef"``).

    Returns:
        wide DataFrame — 행 = concept, 열 = period (contextRef 별). 값 = value
        문자열. 빈 입력 → 빈 DataFrame.

    Raises:
        없음.

    Example:
        >>> wide = horizontalizeFacts(facts)  # doctest: +SKIP
        >>> # 컬럼: concept + 각 contextRef
    """
    if facts.is_empty():
        return facts.head(0)
    if "concept" not in facts.columns or "value" not in facts.columns:
        return facts.head(0)
    if periodCol not in facts.columns:
        return facts.head(0)
    return facts.select(["concept", periodCol, "value"]).pivot(
        on=periodCol, index="concept", values="value", aggregate_function="first"
    )


def fetchHorizontalSlice(
    facts: pl.DataFrame, concepts: list[str], *, periodCol: str = "contextRef", limit: int = 100
) -> pl.DataFrame:
    """``horizontalizeFacts`` 의 단발 + concept 필터 single-call helper.

    Args:
        facts: iXBRL fact DataFrame.
        concepts: 추출할 concept list (예 ``["us-gaap:Revenue"]``).
        periodCol: period 컬럼명.
        limit: 결과 row 수.

    Returns:
        concept × period wide DataFrame (concepts 필터 후 horizontalize).

    Raises:
        없음.

    Example:
        >>> rev = fetchHorizontalSlice(facts, ["us-gaap:Revenue"])  # doctest: +SKIP
    """
    if facts.is_empty():
        return facts.head(0)
    if "concept" not in facts.columns:
        return facts.head(0)
    filtered = facts.filter(pl.col("concept").is_in(concepts))
    if filtered.is_empty():
        return filtered
    wide = horizontalizeFacts(filtered, periodCol=periodCol)
    if limit > 0:
        wide = wide.head(limit)
    return wide


def iterHorizontalSlice(facts: pl.DataFrame, conceptGroups: list[list[str]], *, periodCol: str = "contextRef"):
    """``fetchHorizontalSlice`` 의 streaming pair (룰 10) — 그룹별 yield.

    Args:
        facts: iXBRL fact DataFrame.
        conceptGroups: concept group list (예 ``[["us-gaap:Revenue"], ["us-gaap:Assets"]]``).
        periodCol: period 컬럼명.

    Yields:
        그룹별 wide DataFrame.

    Raises:
        없음.

    Example:
        >>> for slice_ in iterHorizontalSlice(facts, [["us-gaap:Revenue"]]):
        ...     pass  # doctest: +SKIP
    """
    for concepts in conceptGroups:
        yield fetchHorizontalSlice(facts, concepts, periodCol=periodCol)
