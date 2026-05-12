"""Company live filing helpers."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

import polars as pl


def coerceDate(value: str | date | datetime | None) -> date | None:
    """입력값을 date로 정규화한다.

    Args:
        value: 인자.

    Raises:
        없음.

    Example:
        >>> coerceDate(...)

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

    Returns:
        <TODO: return desc> (date | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{8}", text):
        return datetime.strptime(text, "%Y%m%d").date()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return datetime.strptime(text, "%Y-%m-%d").date()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        return datetime.strptime(f"{text}-01", "%Y-%m-%d").date()
    if re.fullmatch(r"\d{4}", text):
        return datetime.strptime(f"{text}-01-01", "%Y-%m-%d").date()
    raise ValueError(f"올바르지 않은 날짜 형식: {value!r}")


def resolveDateWindow(
    start: str | date | datetime | None = None,
    end: str | date | datetime | None = None,
    *,
    days: int | None = None,
) -> tuple[str | None, str | None]:
    """live filings 조회용 날짜 범위를 결정한다.

    Args:
        start: 인자.
        end: 인자.
        days: 인자.

    Raises:
        없음.

    Example:
        >>> resolveDateWindow(...)

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

    Returns:
        <TODO: return desc> (tuple[str | None, str | None])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    startDate = coerceDate(start)
    endDate = coerceDate(end)

    if days is not None:
        if days <= 0:
            raise ValueError("days는 1 이상이어야 합니다.")
        if endDate is None:
            endDate = date.today()
        if startDate is None:
            startDate = endDate - timedelta(days=days - 1)

    return (
        startDate.isoformat() if startDate is not None else None,
        endDate.isoformat() if endDate is not None else None,
    )


def splitKeywords(keyword: str | None) -> list[str]:
    """콤마/공백 기반 키워드 분리.

    Args:
        keyword: 인자.

    Raises:
        없음.

    Example:
        >>> splitKeywords(...)

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

    Returns:
        <TODO: return desc> (list[str])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    if keyword is None:
        return []
    tokens = [token.strip() for token in re.split(r"[,/|\n]+", str(keyword)) if token.strip()]
    return tokens


def filterFilingsByKeyword(df: pl.DataFrame, *, keyword: str | None, columns: list[str]) -> pl.DataFrame:
    """지정 컬럼 기준 keyword 포함 행만 남긴다.

    Args:
        df: 인자.
        keyword: 인자.
        columns: 인자.

    Raises:
        없음.

    Example:
        >>> filterFilingsByKeyword(...)

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

    Returns:
        <TODO: return desc> (pl.DataFrame)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    tokens = splitKeywords(keyword)
    if not tokens or df.is_empty():
        return df

    available = [column for column in columns if column in df.columns]
    if not available:
        return df

    pattern = "(?i)" + "|".join(re.escape(token) for token in tokens)
    expr = pl.lit(False)
    for column in available:
        expr = expr | pl.col(column).cast(pl.Utf8).fill_null("").str.contains(pattern)
    return df.filter(expr)


def filingRecord(value: Any) -> dict[str, Any] | None:
    """row-like filing 입력을 dict로 정규화한다.

    Args:
        value: 인자.

    Raises:
        없음.

    Example:
        >>> filingRecord(...)

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

    Returns:
        <TODO: return desc> (dict[str, Any] | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    if isinstance(value, dict):
        return dict(value)
    return None


def truncateText(text: str, maxChars: int | None = None) -> tuple[str, bool]:
    """문자열을 지정 길이로 자른다.

    Args:
        text: 인자.
        maxChars: 인자.

    Raises:
        없음.

    Example:
        >>> truncateText(...)

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

    Returns:
        <TODO: return desc> (tuple[str, bool])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - datetime
        - polars
    """
    if maxChars is None or maxChars <= 0 or len(text) <= maxChars:
        return text, False
    return text[:maxChars], True
