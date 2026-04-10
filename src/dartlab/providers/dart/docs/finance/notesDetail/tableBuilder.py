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


def buildTableDf(
    allTables: dict,
    unitByYear: dict[str, float] | None = None,
    mapper: NotesMapper | None = None,
) -> pl.DataFrame | None:
    """항목별 시계열 DataFrame 생성 — notesMapper 기반.

    notes 항목별 시계열 DataFrame 생성.
    항목 필터링을 하드코딩 regex 대신 notesMapper.lookup()으로 수행.

    Args:
        allTables: {periodKey: [NotesPeriod, ...]}
        unitByYear: {periodKey: unitScale}
        mapper: NotesMapper (None이면 기본 매퍼 로드)
    """
    import polars as pl

    if mapper is None:
        mapper = NotesMapper()

    from dartlab.core.tableParser import parseAmount

    itemData: dict[str, dict[str, str]] = {}
    colOrder: list[str] = []
    colUnit: dict[str, float] = {}

    for year in sorted(allTables.keys(), reverse=True):
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

            # 매퍼 기반 필터링 — heuristic 대신 데이터
            if mapper.isSkip(normalized):
                continue

            if normalized not in itemData:
                itemData[normalized] = {}
            if item.values:
                picked = pickValue(item.values)
                if not picked:
                    continue
                # 첫 번째 값 우선 (중복 방지)
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


