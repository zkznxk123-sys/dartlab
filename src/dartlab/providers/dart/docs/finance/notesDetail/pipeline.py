"""주석 세부항목 파이프라인.

테이블 빌드는 core/mappers/masterParser.buildTableDf()에 위임.
이 모듈은 데이터 로드 + 섹션 추출 + 테이블 파싱만 담당.
"""

from dartlab.core.dataLoader import PERIOD_KINDS, extractCorpName, loadData
from dartlab.core.notesExtractor import extractNotesContent, findNumberedSection
from dartlab.core.reportSelector import selectReport
from dartlab.core.tableParser import detectUnit, parseNotesTable
from dartlab.providers.dart.docs.finance.notesDetail.types import (
    NOTES_KEYWORDS,
    NotesDetailResult,
    NotesItem,
    NotesPeriod,
)


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
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    keywords = NOTES_KEYWORDS.get(keyword, [keyword])
    kinds = PERIOD_KINDS.get(period, PERIOD_KINDS["y"])
    years = sorted(df["year"].unique().to_list(), reverse=True)

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

    from dartlab.core.mappers.masterParser import buildTableDf
    from dartlab.core.mappers.notesMapper import NotesMapper

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


