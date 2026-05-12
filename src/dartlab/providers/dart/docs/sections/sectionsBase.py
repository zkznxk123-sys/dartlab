"""sections 패키지 공용 상수와 유틸리티."""

from __future__ import annotations

import re

import polars as pl

REPORT_KINDS: list[tuple[str, str]] = [
    ("annual", ""),
    ("Q1", "Q1"),
    ("semi", "Q2"),
    ("Q3", "Q3"),
]

RE_SPLIT_SUFFIX = re.compile(r" \[\d+/\d+\]$")
RE_PERIOD = re.compile(r"^\d{4}(Q[1-4])?$")
RE_ANNUAL_Q4_ALIAS = re.compile(r"^(\d{4})Q4$")


def detectContentCol(df: pl.DataFrame) -> str:
    """detectContentCol — TODO 한국어 동작 설명.

    Args:
        df: 인자.

    Raises:
        없음.

    Example:
        >>> detectContentCol(...)

    Returns:
        str — 변환 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    if "section_content" in df.columns:
        return "section_content"
    return "content"


def periodSortKey(period: str) -> tuple[int, int]:
    """periodSortKey — TODO 한국어 동작 설명.

    Args:
        period: 인자.

    Raises:
        없음.

    Example:
        >>> periodSortKey(...)

    Returns:
        tuple[int, int] — (year, quarter).

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    value = str(period)
    if "Q" in value:
        return int(value[:4]), int(value[-1])
    return int(value), 4


def sortPeriods(periods: list[str], *, descending: bool = False) -> list[str]:
    """sortPeriods — TODO 한국어 동작 설명.

    Args:
        periods: 인자.
        descending: 인자.

    Raises:
        없음.

    Example:
        >>> sortPeriods(...)

    Returns:
        list[str] — 결과 목록.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    return sorted(periods, key=periodSortKey, reverse=descending)


def periodOrderValue(period: str) -> int:
    """periodOrderValue — TODO 한국어 동작 설명.

    Args:
        period: 인자.

    Raises:
        없음.

    Example:
        >>> periodOrderValue(...)

    Returns:
        int — 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    year, slot = periodSortKey(period)
    return year * 10 + slot


def basePath(path: str) -> str:
    """basePath — TODO 한국어 동작 설명.

    Args:
        path: 인자.

    Raises:
        없음.

    Example:
        >>> basePath(...)

    Returns:
        str — 변환 결과.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    return RE_SPLIT_SUFFIX.sub("", path)


def rawPeriod(period: str) -> str:
    """rawPeriod — TODO 한국어 동작 설명.

    Args:
        period: 인자.

    Raises:
        없음.

    Example:
        >>> rawPeriod(...)

    Returns:
        str — 변환 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    value = str(period).strip()
    match = RE_ANNUAL_Q4_ALIAS.fullmatch(value)
    if match:
        return match.group(1)
    return value


def displayPeriod(period: str, *, annualAsQ4: bool = False) -> str:
    """displayPeriod — TODO 한국어 동작 설명.

    Args:
        period: 인자.
        annualAsQ4: 인자.

    Raises:
        없음.

    Example:
        >>> displayPeriod(...)

    Returns:
        str — 변환 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    value = rawPeriod(period)
    if annualAsQ4 and RE_PERIOD.fullmatch(value) and "Q" not in value:
        return f"{value}Q4"
    return value


def periodColumns(
    columns: list[str],
    *,
    descending: bool = False,
    annualAsQ4: bool = False,
) -> list[str]:
    """periodColumns — TODO 한국어 동작 설명.

    Args:
        columns: 인자.
        descending: 인자.
        annualAsQ4: 인자.

    Raises:
        없음.

    Example:
        >>> periodColumns(...)

    Returns:
        list[str] — 결과 목록.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    ordered = sortPeriods([str(col) for col in columns if RE_PERIOD.fullmatch(str(col))], descending=descending)
    return [displayPeriod(period, annualAsQ4=annualAsQ4) for period in ordered]


def formatPeriodRange(
    periods: list[str],
    *,
    descending: bool = False,
    annualAsQ4: bool = False,
) -> str:
    """formatPeriodRange — TODO 한국어 동작 설명.

    Args:
        periods: 인자.
        descending: 인자.
        annualAsQ4: 인자.

    Raises:
        없음.

    Example:
        >>> formatPeriodRange(...)

    Returns:
        str — 변환 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    ordered = sortPeriods([rawPeriod(period) for period in periods], descending=descending)
    if not ordered:
        return "-"
    labels = [displayPeriod(period, annualAsQ4=annualAsQ4) for period in ordered]
    return f"{labels[0]}..{labels[-1]}" if len(labels) > 1 else labels[0]


def reorderPeriodColumns(
    df: pl.DataFrame,
    *,
    descending: bool = False,
    annualAsQ4: bool = False,
) -> pl.DataFrame:
    """reorderPeriodColumns — TODO 한국어 동작 설명.

    Args:
        df: 인자.
        descending: 인자.
        annualAsQ4: 인자.

    Raises:
        없음.

    Example:
        >>> reorderPeriodColumns(...)

    Returns:
        pl.DataFrame — 결과.

    SeeAlso:
        - ``REPORT_KINDS`` / ``RE_PERIOD`` / ``RE_ANNUAL_Q4_ALIAS`` — 본 모듈 상수.
        - ``pipeline.py`` — sections 빌더 owner.

    Requires:
        - polars

    Capabilities:
        - sections pipeline 공용 stateless utility (content col 탐지, period parsing, basePath 등).

    Guide:
        - 사용자 API 는 ``c.sections`` — 본 모듈 직접 호출 X.

    AIContext:
        internal sections base — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections pipeline 내부 stateless utility.
            - REPORT_KINDS / RE_PERIOD 정규식 외부 의존 가정 X.
        OutputSchema:
            - str / bool / pl.DataFrame / list — 함수별.
        Prerequisites:
            - 본 회사 docs sections 본문.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - 입력 → stateless 변환 → 본 함수.
        TargetMarkets:
            - KR (DART) sections base.
    """
    periodCols = [str(col) for col in df.columns if RE_PERIOD.fullmatch(str(col))]
    if not periodCols:
        return df

    orderedPeriods = sortPeriods(periodCols, descending=descending)
    metaCols = [col for col in df.columns if col not in periodCols]
    result = df.select(metaCols + orderedPeriods)
    if not annualAsQ4:
        return result

    existing = set(result.columns)
    renameMap: dict[str, str] = {}
    for period in orderedPeriods:
        label = displayPeriod(period, annualAsQ4=True)
        if label == period:
            continue
        if label in existing and label != period:
            continue
        renameMap[period] = label
    return result.rename(renameMap) if renameMap else result
