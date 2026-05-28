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
    """본문 컬럼명 탐지 — ``section_content`` 우선, 없으면 ``content``.

    Args:
        df: sections parquet 조각.

    Returns:
        본문이 담긴 컬럼명 (``"section_content"`` 또는 ``"content"``).

    Raises:
        없음.

    Example:
        >>> detectContentCol(df)
        'section_content'
    """
    if "section_content" in df.columns:
        return "section_content"
    return "content"


def periodSortKey(period: str) -> tuple[int, int]:
    """period 문자열 → 정렬 키 ``(year, quarter)``. annual = quarter 4.

    Args:
        period: ``"2024"`` (annual) 또는 ``"2024Q3"`` (분기) 형식.

    Returns:
        ``(year, quarter)`` tuple — annual 은 (year, 4).

    Raises:
        ValueError: 형식 위반.

    Example:
        >>> periodSortKey("2024Q3")
        (2024, 3)
    """
    value = str(period)
    if "Q" in value:
        return int(value[:4]), int(value[-1])
    return int(value), 4


def sortPeriods(periods: list[str], *, descending: bool = False) -> list[str]:
    """period 리스트 정렬 — ``periodSortKey`` 기준 (year × 4 + quarter).

    Args:
        periods: ``["2024", "2023Q3", ...]``.
        descending: True 면 최신 우선.

    Returns:
        정렬된 list.

    Raises:
        ValueError: ``periodSortKey`` 형식 위반.

    Example:
        >>> sortPeriods(["2023", "2024Q1", "2023Q3"], descending=True)
        ['2024Q1', '2023', '2023Q3']
    """
    return sorted(periods, key=periodSortKey, reverse=descending)


def periodOrderValue(period: str) -> int:
    """period → 단일 정수 순위 (``year × 10 + quarter``) — sort 또는 직접 비교용.

    Args:
        period: ``"2024"`` / ``"2024Q3"``.

    Returns:
        ``year * 10 + quarter`` (annual = quarter 4).

    Raises:
        ValueError: ``periodSortKey`` 형식 위반.

    Example:
        >>> periodOrderValue("2024Q3")
        20243
    """
    year, slot = periodSortKey(period)
    return year * 10 + slot


def basePath(path: str) -> str:
    """sections path 의 ``-split-N`` suffix 제거 — semantic 동치 path 매칭용.

    Args:
        path: ``"sec01-split-3"`` 같은 path.

    Returns:
        suffix 제거 후 base path (``"sec01"``).

    Raises:
        없음.

    Example:
        >>> basePath("sec01-split-3")
        'sec01'
    """
    return RE_SPLIT_SUFFIX.sub("", path)


def rawPeriod(period: str) -> str:
    """annual-Q4 alias (``"2024Q4"`` 등) → raw annual (``"2024"``). 다른 형식은 그대로.

    Args:
        period: ``"2024"`` / ``"2024Q4"`` / ``"2024Q3"``.

    Returns:
        annual alias 면 raw annual, 아니면 입력 그대로.

    Raises:
        없음.

    Example:
        >>> rawPeriod("2024Q4")
        '2024'
    """
    value = str(period).strip()
    match = RE_ANNUAL_Q4_ALIAS.fullmatch(value)
    if match:
        return match.group(1)
    return value


def displayPeriod(period: str, *, annualAsQ4: bool = False) -> str:
    """사용자 표시용 period — annual 을 Q4 표기로 정규화 옵션.

    Args:
        period: 입력 period (annual / 분기 / alias).
        annualAsQ4: True 면 annual ``"2024"`` → ``"2024Q4"`` 변환.

    Returns:
        표시용 period 문자열.

    Raises:
        없음.

    Example:
        >>> displayPeriod("2024", annualAsQ4=True)
        '2024Q4'
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
    """columns 중 period 형식 매칭만 추출 → 정렬 + (옵션) annual-Q4 표기.

    Args:
        columns: DataFrame columns list.
        descending: True 면 최신 우선.
        annualAsQ4: True 면 annual → ``"YYYYQ4"`` 변환.

    Returns:
        period 컬럼만 정렬된 list.

    Raises:
        없음.

    Example:
        >>> periodColumns(["topic", "2023", "2024Q1"], descending=True)
        ['2024Q1', '2023']
    """
    ordered = sortPeriods([str(col) for col in columns if RE_PERIOD.fullmatch(str(col))], descending=descending)
    return [displayPeriod(period, annualAsQ4=annualAsQ4) for period in ordered]


def formatPeriodRange(
    periods: list[str],
    *,
    descending: bool = False,
    annualAsQ4: bool = False,
) -> str:
    """period 리스트 → ``"earliest..latest"`` 표기. 1 개면 단일 period, 0 개면 ``"-"``.

    Args:
        periods: period list.
        descending: True 면 정렬 방향 역.
        annualAsQ4: annual → Q4 표기.

    Returns:
        ``"2023Q1..2024Q4"`` 같은 range 문자열 (1 개면 그 period, 0 개면 ``"-"``).

    Raises:
        없음.

    Example:
        >>> formatPeriodRange(["2024", "2023Q1"])
        '2023Q1..2024'
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
    """DataFrame 의 period 컬럼만 ``periodSortKey`` 기준 재정렬 + (옵션) annual → Q4 rename.

    Args:
        df: meta + period 컬럼이 섞인 wide DataFrame.
        descending: 최신 우선.
        annualAsQ4: annual 컬럼명을 ``"YYYYQ4"`` 로 rename.

    Returns:
        meta 컬럼은 원래 순서 유지 + period 컬럼만 재정렬된 DataFrame.

    Raises:
        없음.

    Example:
        >>> reorderPeriodColumns(df, descending=True)
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
