"""주석 세부항목 파이프라인.

테이블 빌드는 notesDetail/tableBuilder.buildTableDf()에 위임.
이 모듈은 데이터 로드 + 섹션 추출 + 테이블 파싱만 담당.


P2 통합: 기존 notesDetail/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import PERIOD_KINDS, extractCorpName, loadData
from dartlab.core.utils.unitNormalize import normalizeFromUnitScale
from dartlab.providers.mappers.common import isCurrentPeriod, normalizeName, pickValue
from dartlab.providers.mappers.notesMapper import NOTES_KEYWORDS, NotesMapper
from dartlab.providers.notesExtractor import extractNotesContent, findNumberedSection
from dartlab.providers.reportSelector import selectReport
from dartlab.providers.tableParser import detectUnit, parseAmount, parseNotesTable

if TYPE_CHECKING:
    import polars as pl


# types
# NOTES_KEYWORDS 단일 진실의 원천: core/mappers/notesMapper.py


@dataclass
class NotesItem:
    """주석 테이블의 한 행."""

    name: str
    values: list[str]


@dataclass
class NotesPeriod:
    """주석 테이블의 한 기간 블록."""

    pattern: str
    period: str
    headers: list[str]
    items: list[NotesItem]


@dataclass
class NotesDetailResult:
    """주석 세부항목 분석 결과."""

    corpName: str | None
    keyword: str
    nYears: int = 0
    unit: float = 1.0
    tables: dict[str, list[NotesPeriod]] | None = None
    tableDf: pl.DataFrame | None = None


# parser
_MAX_YEARS = 5  # 최근 N년만 반환 (sparse 방지)
_SPARSE_THRESHOLD = 0.8  # None 비율 이 이상이면 행 제거


def buildTableDf(
    allTables: dict,
    unitByYear: dict[str, float] | None = None,
    mapper: NotesMapper | None = None,
    *,
    maxYears: int = _MAX_YEARS,
) -> pl.DataFrame | None:
    """항목별 시계열 DataFrame 생성 — notesMapper 기반.

    notes 항목별 시계열 DataFrame 생성.
    항목 필터링을 notesMapper로, 연도 범위를 maxYears로 제한.
    None 비율 80%+ 행은 자동 제거 (sparse 방지).

    Args:
        allTables: {periodKey: [NotesPeriod, ...]}
        unitByYear: {periodKey: unitScale}
        mapper: NotesMapper (None이면 기본 매퍼 로드)
        maxYears: 최근 N년만 반환 (기본 5)

    Raises:
        없음.

    Example:
        >>> buildTableDf(...)

    Returns:
        pl.DataFrame | None — 결과.
    """
    import polars as pl

    if mapper is None:
        mapper = NotesMapper()

    # 최근 N년만 선택
    sortedYears = sorted(allTables.keys(), reverse=True)[:maxYears]

    itemData: dict[str, dict[str, str]] = {}
    colOrder: list[str] = []
    colUnit: dict[str, float] = {}

    for year in sortedYears:
        periods = allTables[year]
        # 당기 블록 선택
        currentBlock = None
        for p in periods:
            if isCurrentPeriod(p.period):
                currentBlock = p
                break
        if currentBlock is None:
            currentBlock = periods[0]

        colName = year
        if colName not in colOrder:
            colOrder.append(colName)
        colUnit[colName] = (unitByYear or {}).get(year, 1.0)

        for item in currentBlock.items:
            normalized = normalizeName(item.name)

            # 매퍼 기반 필터링
            if mapper.isSkip(normalized):
                continue

            # alias 정규화 — 연도 간 같은 항목의 다른 이름을 canonical로 통합
            normalized = mapper.resolveAlias(normalized)
            if normalized.startswith("_skip_"):
                continue

            if normalized not in itemData:
                itemData[normalized] = {}
            if item.values:
                picked = pickValue(item.values)
                if not picked:
                    continue
                if colName not in itemData[normalized]:
                    itemData[normalized][colName] = picked

    if not itemData:
        return None

    rows = []
    nCols = len(colOrder)
    for name, vals in itemData.items():
        row: dict[str, object] = {"항목": name}
        noneCount = 0
        for col in colOrder:
            raw = vals.get(col, "")
            parsed = parseAmount(raw)
            unit = colUnit.get(col, 1.0)
            val = normalizeFromUnitScale(parsed, unit)
            row[col] = val
            if val is None:
                noneCount += 1
        # sparse 행 제거 — None 비율 80%+ 행은 노이즈
        if nCols > 0 and noneCount / nCols >= _SPARSE_THRESHOLD:
            continue
        rows.append(row)

    if not rows:
        return None

    schema: dict[str, type] = {"항목": pl.Utf8}
    for col in colOrder:
        schema[col] = pl.Float64
    return pl.DataFrame(rows, schema=schema)


# pipeline
def notesDetail(
    stockCode: str,
    keyword: str,
    period: str = "y",
) -> NotesDetailResult | None:
    """주석 세부항목 테이블 추출.

    Args:
        stockCode: 종목코드 (6자리)
        keyword: 주석 키워드 (NOTES_KEYWORDS 참조, 23개 지원)
        period: "y" (연간) | "q" (분기) | "h" (반기)

    Returns:
        NotesDetailResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> notesDetail(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    keywords = NOTES_KEYWORDS.get(keyword, [keyword])
    kinds = PERIOD_KINDS.get(period, PERIOD_KINDS["y"])
    years = sorted(df["year"].unique().to_list(), reverse=True)[:5]  # 최근 5년

    allTables: dict[str, list[NotesPeriod]] = {}
    unitByYear: dict[str, float] = {}
    latestUnit = 1.0

    for year in years:
        for kind in kinds:
            report = selectReport(df, year, reportKind=kind)
            if report is None:
                continue

            contents = extractNotesContent(report)
            if not contents:
                continue

            section = None
            for kw in keywords:
                section = findNumberedSection(contents, kw)
                if section is not None:
                    break
            if section is None:
                continue

            parsed = parseNotesTable(section)
            if not parsed:
                continue

            unit = detectUnit(section)
            if not allTables:
                latestUnit = unit

            periods = []
            for block in parsed:
                items = [NotesItem(name=it["name"], values=it["values"]) for it in block["items"]]
                periods.append(
                    NotesPeriod(
                        pattern=block["pattern"],
                        period=block["period"],
                        headers=block["headers"],
                        items=items,
                    )
                )

            if periods:
                # 분기 키: "2024Q1", "2024H1", "2024Q3", "2024" (연간)
                periodKey = _makePeriodKey(year, kind)
                allTables[periodKey] = periods
                unitByYear[periodKey] = unit

    if not allTables:
        return None

    from dartlab.providers.dart.docs.finance.notesDetail.tableBuilder import buildTableDf
    from dartlab.providers.mappers.notesMapper import NotesMapper

    tableDf = buildTableDf(allTables, unitByYear, mapper=NotesMapper())

    return NotesDetailResult(
        corpName=corpName,
        keyword=keyword,
        nYears=len(allTables),
        unit=latestUnit,
        tables=allTables,
        tableDf=tableDf,
    )


_KIND_SUFFIX = {
    "annual": "",
    "Q1": "Q1",
    "semi": "H1",
    "Q3": "Q3",
}


def _makePeriodKey(year: str, kind: str) -> str:
    """연도 + 보고서 종류 → 기간 키."""
    suffix = _KIND_SUFFIX.get(kind, "")
    return f"{year}{suffix}" if suffix else year
