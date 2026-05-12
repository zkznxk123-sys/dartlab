"""EDINET sections 수평화 파이프라인.

docs parquet → section 매핑 → topic × period 수평화.
DART/EDGAR sections pipeline과 동일한 패턴.
"""

from __future__ import annotations

from typing import Any

import polars as pl

from dartlab.providers.edinet.docs.sections.mapper import (
    mapSectionTitle,
    normalizeSectionTitle,
)


def buildSections(docsDf: pl.DataFrame) -> pl.DataFrame:
    """docs parquet → sections DataFrame 변환.

    Args:
        docsDf: docs parquet (edinet_code, element_id, label, context_id, text).

    Returns:
        sections DataFrame (topic, period, text, ...).

    Raises:
        없음.

    Example:
        >>> buildSections(...)

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    if docsDf.is_empty():
        return pl.DataFrame(
            schema={
                "topic": pl.Utf8,
                "period": pl.Utf8,
                "text": pl.Utf8,
                "sourceLabel": pl.Utf8,
                "elementId": pl.Utf8,
            }
        )

    rows: list[dict[str, Any]] = []

    for row in docsDf.iter_rows(named=True):
        label = row.get("label", "")
        topicId = mapSectionTitle(label)
        if topicId is None:
            topicId = normalizeSectionTitle(label)

        # context_id에서 period 추출
        # EDINET context 형식: CurrentYearDuration, Prior1YearDuration 등
        contextId = row.get("context_id", "")
        period = _parsePeriod(contextId)

        rows.append(
            {
                "topic": topicId,
                "period": period,
                "text": row.get("text", ""),
                "sourceLabel": label,
                "elementId": row.get("element_id", ""),
            }
        )

    return pl.DataFrame(rows)


def _parsePeriod(contextId: str) -> str:
    """EDINET context ID → period 문자열.

    EDINET context 패턴:
    - CurrentYearDuration → 당기
    - Prior1YearDuration → 전기
    - CurrentYearInstant → 당기말
    - Prior1YearInstant → 전기말
    - CurrentQuarter1Duration → 1Q
    """
    if not contextId:
        return ""

    ctx = contextId.lower()

    if "currentyear" in ctx:
        if "instant" in ctx:
            return "currentEnd"
        return "current"
    if "prior1year" in ctx:
        if "instant" in ctx:
            return "prior1End"
        return "prior1"
    if "prior2year" in ctx:
        if "instant" in ctx:
            return "prior2End"
        return "prior2"

    # 분기 패턴
    if "currentquarter" in ctx:
        return "currentQ"
    if "prior1quarter" in ctx:
        return "prior1Q"

    return contextId
