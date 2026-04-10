"""Notes Master Parser — notesMapper 기반 파서.

기존 pipeline.py(legacyParser)와 동일한 인터페이스.
notesMapper가 항목 유형(amount/rate/text)과 외화 여부를 판단하므로
하드코딩 heuristic 없이 구조 데이터만으로 파싱.

교체 순서:
1. masterParser 만들고 동일 인터페이스
2. 6종목에서 legacy vs master 결과 비교
3. 일치율 95%+ → 해당 notes 항목 master로 전환
4. 항목별로 순차 전환
5. 전 항목 전환 완료 → legacy 제거
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

from dartlab.core.mappers.notesMapper import NotesMapper


def _normalizeName(name: str) -> str:
    """항목명 정규화. 한글 사이 공백 제거."""
    return re.sub(r"(?<=[\uAC00-\uD7A3])\s+(?=[\uAC00-\uD7A3])", "", name.strip())


_CURRENT_PERIOD = re.compile(r"(당기|당기말|당반기|당분기|현재|전체)")


def _isCurrentPeriod(period: str) -> bool:
    """당기 계열 period인지 판정."""
    if re.search(r"(전기|전반기|전분기)", period):
        return False
    return bool(_CURRENT_PERIOD.search(period))


# 외화 통화코드 — 값 수준 감지 (매퍼와 독립, 값에 외화가 섞인 경우)
_FOREIGN_CURRENCY_RE = re.compile(
    r"(USD|JPY|EUR|GBP|CNY|HKD|SGD|AUD|CAD|CHF|TWD|THB|INR|VND|MYR|IDR|PHP|BRL|MXN|ZAR)"
    r"|(\[.*?천\])"
    r"|(JP￥|US\$|€|£|¥|￥)"
    r"|(\(.*?천\))"
)


def _hasForeignCurrencyInValue(value: str) -> bool:
    """값에 외화 통화코드/기호가 포함되어 있는지."""
    return bool(_FOREIGN_CURRENCY_RE.search(value))


def _pickValue(values: list[str], mapper: NotesMapper, itemName: str) -> str:
    """값 리스트에서 대표값 선택.

    항상 원화 값 우선. 외화 통화코드가 포함된 값은 건너뛴다.
    원화 값이 없을 때만 fallback으로 아무 유효값 선택.
    """
    # 1차: 원화 값 (외화 코드 없는 것)
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if not v_stripped or v_stripped == "-":
            continue
        if _hasForeignCurrencyInValue(v_stripped):
            continue
        return v_stripped

    # 2차: fallback — 아무 유효값
    for v in reversed(values):
        v_stripped = (v or "").strip()
        if v_stripped and v_stripped != "-":
            return v_stripped

    return values[0] if values else ""


def buildTableDf(
    allTables: dict,
    unitByYear: dict[str, float] | None = None,
    mapper: NotesMapper | None = None,
) -> pl.DataFrame | None:
    """항목별 시계열 DataFrame 생성 — notesMapper 기반.

    기존 pipeline._buildTableDf()와 동일한 출력이지만,
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

            # 매퍼 기반 필터링 — heuristic 대신 데이터
            if mapper.isSkip(normalized):
                continue

            if normalized not in itemData:
                itemData[normalized] = {}
            if item.values:
                picked = _pickValue(item.values, mapper, normalized)
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


