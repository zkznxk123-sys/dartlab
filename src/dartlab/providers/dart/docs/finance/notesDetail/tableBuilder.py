"""notes 테이블 빌더 — notesMapper 기반.

pipeline.py가 추출한 raw 테이블 데이터를 항목별 시계열 DataFrame으로 변환.
항목 필터링(amount/rate/text)은 notesMapper(데이터 기반)로 수행.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from dartlab.core.mappers.common import isCurrentPeriod, normalizeName, pickValue
from dartlab.core.mappers.notesMapper import NotesMapper

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
    """
    import polars as pl

    if mapper is None:
        mapper = NotesMapper()

    from dartlab.core.tableParser import parseAmount

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

    from dartlab.core.finance.unitNormalize import normalizeFromUnitScale

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
