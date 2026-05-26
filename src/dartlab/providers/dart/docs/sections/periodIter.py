"""sections period subset 순회 + period sort key.

``iterPeriodSubsets(stockCode)`` 가 ``docs.parquet`` 을 1 회 load 한 뒤
(year, reportKind) 기간별 subset 을 yield. 정정공시 정책은
``selectReport`` 위임 (silent drop 시 logger.info).

본 모듈은 ``pipeline.py`` 에서 분리됨 (operation.sectionsRefactor §5 부채 1).
caller API 0 변경 — pipeline.py 가 본 함수들을 re-import.
"""

from __future__ import annotations

from collections.abc import Iterator

import polars as pl

from dartlab.core.dataLoader import loadData
from dartlab.providers.dart.docs.sections.sectionsBase import REPORT_KINDS, detectContentCol
from dartlab.providers.reportSelector import selectReport


def _periodSortKey(period: str) -> tuple[int, int]:
    year = int(period[:4])
    if period.endswith("Q1"):
        return (year, 1)
    if period.endswith("Q2"):
        return (year, 2)
    if period.endswith("Q3"):
        return (year, 3)
    return (year, 4)


_SECTIONS_REQUIRED_COLS = [
    "year",
    "report_type",
    "rcept_date",
    "section_order",
    "section_title",
    "section_content",
    "content",
]


def iterPeriodSubsets(
    stockCode: str,
    *,
    sinceYear: int = 2016,
) -> Iterator[tuple[str, str, str, pl.DataFrame]]:
    """기간별 유효 섹션 subset을 순회한다.

    Yields:
        (periodKey, reportKind, contentCol, subset) 튜플.
        subset은 section_order 기준 정렬된 DataFrame.

    loadData를 1회만 호출하고, pipeline/views 양쪽이 공유한다.
    sinceYear 이전 기간은 건너뛴다 (finance 없는 기간 제외).

    Args:
        stockCode: 종목 코드.
        sinceYear: 이 연도 미만 기간 skip (default 2016).

    Returns:
        Iterator — (period, reportKind, contentCol, DataFrame) 튜플.

    Raises:
        없음.

    Example:
        >>> for periodKey, reportKind, ccol, subset in iterPeriodSubsets("005930"):
        ...     pass
    """
    df = loadData(stockCode, sinceYear=sinceYear, columns=_SECTIONS_REQUIRED_COLS)
    ccol = detectContentCol(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    for year in years:
        if isinstance(year, str) and year.isdigit() and int(year) < sinceYear:
            continue
        if isinstance(year, (int, float)) and int(year) < sinceYear:
            continue
        for reportKind, suffix in REPORT_KINDS:
            periodKey = f"{year}{suffix}"
            report = selectReport(df, year, reportKind=reportKind)
            if report is None or ccol not in report.columns:
                continue
            subset = (
                report.select(["section_order", "section_title", ccol])
                .with_columns(pl.col("section_title").cast(pl.Utf8))
                .filter(
                    (pl.col(ccol).is_not_null() & (pl.col(ccol).str.len_chars() > 0))
                    # Roman chapter (`I./II./III./...`) 본문이 empty 라도 currentMajorNum
                    # 추적용 marker 로 통과. 새 양식 (parseSectionsByTitle 의 TITLE 단위 분리) 가
                    # Roman 직속 본문 = "" 로 emit — 옛 SECTION-1/2 양식과 호환 위해 예외 통과.
                    | pl.col("section_title").str.contains(r"^[IVXivx]+\.\s")
                )
                .sort("section_order")
            )
            if subset.height == 0:
                continue
            yield periodKey, reportKind, ccol, subset
