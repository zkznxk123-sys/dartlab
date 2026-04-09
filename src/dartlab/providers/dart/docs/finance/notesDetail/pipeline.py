"""주석 세부항목 파이프라인."""

import re

import polars as pl

from dartlab.core.dataLoader import PERIOD_KINDS, extractCorpName, loadData
from dartlab.core.notesExtractor import extractNotesContent, findNumberedSection
from dartlab.core.reportSelector import selectReport
from dartlab.core.tableParser import detectUnit, parseAmount, parseNotesTable
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

    tableDf = _buildTableDf(allTables, unitByYear)

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


def _normalizeName(name: str) -> str:
    """항목명 정규화. 한글 사이 공백 제거."""
    return re.sub(r"(?<=[\uAC00-\uD7A3])\s+(?=[\uAC00-\uD7A3])", "", name.strip())


# 외화 통화코드 — 이 문자열이 포함된 값은 원화가 아님
_FOREIGN_CURRENCY_RE = re.compile(
    r"(USD|JPY|EUR|GBP|CNY|HKD|SGD|AUD|CAD|CHF|TWD|THB|INR|VND|MYR|IDR|PHP|BRL|MXN|ZAR)"
    r"|(\[.*?천\])"  # "[USD, 천]" 같은 패턴
    r"|(JP￥|US\$|€|£|¥|￥)"  # 통화 기호
    r"|(\(.*?천\))"  # "(JP￥ 18,500,000천)" 같은 괄호 패턴
)


def _hasForeignCurrency(value: str) -> bool:
    """외화 통화코드가 포함된 값인지 판별."""
    return bool(_FOREIGN_CURRENCY_RE.search(value))


def _pickValue(values: list[str]) -> str:
    """값 리스트에서 대표값 선택.

    우선순위:
    1. 외화 통화코드가 없는 원화 숫자값 (마지막)
    2. 그래도 없으면 아무 유효값 (마지막)
    """
    # 1차: 원화 값만 (외화 코드 없는 숫자)
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if not v_stripped or v_stripped == "-":
            continue
        if _hasForeignCurrency(v_stripped):
            continue
        return v_stripped
    # 2차: 외화 포함이라도 유효하면 (fallback)
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if v_stripped and v_stripped != "-":
            return v_stripped
    return values[0] if values else ""


_CURRENT_PERIOD = re.compile(r"(당기|당기말|당반기|당분기|현재|전체)")


def _isCurrentPeriod(period: str) -> bool:
    """당기 계열 period인지 판정. 전기/전기말은 제외."""
    if re.search(r"(전기|전반기|전분기)", period):
        return False
    return bool(_CURRENT_PERIOD.search(period))


# 비금액 행 — 이자율, 기술, 설명 등. 단위 변환하면 안 되는 항목.
_NON_AMOUNT_PATTERNS = re.compile(
    r"(연이자율|이자율|기술$|설명$|기술:$|에\s*대한\s*(기술|설명))",
    re.IGNORECASE,
)


def _isNonAmountRow(name: str) -> bool:
    """금액이 아닌 행(이자율, 텍스트 기술 등) 필터."""
    return bool(_NON_AMOUNT_PATTERNS.search(name))


def _buildTableDf(
    allTables: dict[str, list[NotesPeriod]],
    unitByYear: dict[str, float] | None = None,
) -> pl.DataFrame | None:
    """항목별 시계열 DataFrame 생성.

    각 연도에서 당기 블록만 선택하여 연도 컬럼으로 정렬.
    전기 블록은 이전 연도 당기와 중복이므로 제외.

    단위 정규화: 모든 값을 **원 단위(KRW)** 로 변환.
    `core/constants.py::UNIT_SCALE` 은 백만원=1.0 이라 colUnit 곱셈 후 백만원이 된다.
    여기서 추가로 ×1_000_000 하여 c.IS/c.BS/c.CF 와 동일한 원 단위로 노출.

    비금액 행(연이자율, 기술/설명 텍스트)은 제외 — 단위 변환 시 의미 왜곡 방지.
    """
    itemData: dict[str, dict[str, str]] = {}
    colOrder: list[str] = []
    colUnit: dict[str, float] = {}

    for year in sorted(allTables.keys(), reverse=True):
        periods = allTables[year]
        # 당기 블록 선택 (없으면 첫 번째 블록 사용)
        currentBlock = None
        for p in periods:
            if _isCurrentPeriod(p.period):
                currentBlock = p
                break
        if currentBlock is None:
            currentBlock = periods[0]

        colName = year
        if colName not in colOrder:
            colOrder.append(colName)
        colUnit[colName] = (unitByYear or {}).get(year, 1.0)

        for item in currentBlock.items:
            normalized = _normalizeName(item.name)
            # 비금액 행(이자율, 텍스트 기술) 제외 — 단위 변환 시 의미 왜곡 방지
            if _isNonAmountRow(normalized):
                continue
            if normalized not in itemData:
                itemData[normalized] = {}
            if item.values:
                picked = _pickValue(item.values)
                if not picked:
                    continue
                # 같은 항목명이 이미 있으면 덮어쓰지 않는다 (첫 번째 원화 값 우선).
                # NAVER처럼 "외화대출"이 20행 반복되는 경우 마지막 행이 덮어쓰면
                # 외화 금액이 원화로 이중 변환되는 문제 발생.
                if colName not in itemData[normalized]:
                    itemData[normalized][colName] = picked

    if not itemData:
        return None

    from dartlab.core.finance.unitNormalize import normalizeFromUnitScale

    rows = []
    for name, vals in itemData.items():
        row: dict[str, object] = {"항목": name}
        for col in colOrder:
            raw = vals.get(col, "")
            parsed = parseAmount(raw)
            unit = colUnit.get(col, 1.0)
            row[col] = normalizeFromUnitScale(parsed, unit)
        rows.append(row)

    schema: dict[str, type] = {"항목": pl.Utf8}
    for col in colOrder:
        schema[col] = pl.Float64
    return pl.DataFrame(rows, schema=schema)
