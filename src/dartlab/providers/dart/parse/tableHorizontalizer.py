"""sections 내 markdown 테이블 수평화.

company.py에서 분리된 _horizontalizeTableBlock / _stripUnitHeader.
docs table 블록의 기간별 markdown을 항목×기간 DataFrame으로 변환한다.
"""

from __future__ import annotations

import re

import polars as pl

_UNIT_ONLY_RE = re.compile(
    r"^[\(\[\（<〈]?\s*"
    r"(?:<[^>]+>\s*)?"
    r"[\(\[\（]?\s*"
    r"(?:단위|원화\s*단위|외화\s*단위|금액\s*단위)"
    r".*$",
    re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(r"^\(?\s*기준일\s*:")


def stripUnitHeader(sub: list[str]) -> list[str] | None:
    """단위행/기준일행이 헤더인 서브테이블 → 단위행 제거 + 나머지 반환.

    패턴: | (단위:천원) | | | → sep → 실제헤더 → 데이터
    다중컬럼: | (기준일 : | 2018년 03월 31일 | ) | (단위 : 주) |
    반환: 실제헤더 행부터의 서브테이블 (기존 파서가 그대로 동작).
    해당하지 않으면 None.

    Args:
        sub: 인자.

    Raises:
        없음.

    Example:
        >>> stripUnitHeader(...)
    """
    firstRow = None
    for line in sub:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            continue
        firstRow = [c for c in cells if c.strip()]
        break

    if firstRow is None:
        return None

    if len(firstRow) == 1:
        h = firstRow[0].strip()
        if not (_UNIT_ONLY_RE.match(h) or _DATE_ONLY_RE.match(h)):
            return None
    else:
        joined = " ".join(c.strip() for c in firstRow)
        hasUnit = bool(re.search(r"단위\s*[:/]", joined))
        hasDate = bool(re.search(r"기준일\s*[:/]", joined))
        if not (hasUnit or hasDate):
            return None

    sepIdx = -1
    for i, line in enumerate(sub):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            sepIdx = i
            break

    if sepIdx < 0 or sepIdx + 1 >= len(sub):
        return None

    remainder = sub[sepIdx + 1 :]
    if not remainder:
        return None

    hasSep = any(
        all(set(c.strip()) <= {"-", ":"} for c in line.strip("|").split("|") if c.strip()) for line in remainder
    )
    if hasSep:
        return remainder

    if len(remainder) >= 2:
        headerLine = remainder[0]
        colCount = len(headerLine.strip("|").split("|"))
        sepLine = "| " + " | ".join(["---"] * colCount) + " |"
        return [headerLine, sepLine] + remainder[1:]

    return None


_HZ_SUFFIX_RE = re.compile(r"(사업)?부문$")
_HZ_KISU_RE = re.compile(r"제\d+기\s*(?:\d*분기|반기|말)?\s*" r"\(?(당기|전기|전전기|당반기|전반기|당분기|전분기)\)?")
_HZ_NOTE_REF_RE = re.compile(r"\(\*\d*(?:,\d+)*\)")
_HZ_PERIOD_KW_RE = re.compile(r"\d*분기|반기|당기|전기|전전기|당반기|전반기|당분기|전분기|당기말|전기말")


def _hzNormalizeItem(name: str) -> str:
    """항목명 정규화 — 부문/주석/기수 suffix 제거."""
    name = _HZ_SUFFIX_RE.sub("", name).strip()
    name = _HZ_NOTE_REF_RE.sub("", name).strip()
    m = _HZ_KISU_RE.search(name)
    return m.group(1) if m else name


def _hzGroupHeader(hc: list[str]) -> str:
    """헤더 시그니처 — 기간 키워드 제거 후 normalize."""
    from dartlab.providers.dart.docs.sections.tableParser import _normalizeHeader

    h = _normalizeHeader(hc)
    h = _HZ_PERIOD_KW_RE.sub("", h)
    h = re.sub(r"\| *\|", "|", h)
    return re.sub(r"\s+", " ", h).strip()


def _hzFixSubtable(sub, hc, dr):
    """dr 비어 있으면 stripUnitHeader 로 재파싱. 반환: (sub, hc, dr) or None (불가)."""
    from dartlab.providers.dart.docs.sections.tableParser import (
        _dataRows,
        _headerCells,
        _isJunk,
    )

    if dr:
        return sub, hc, dr
    fixed = stripUnitHeader(sub)
    if fixed is None:
        return None
    fHc = _headerCells(fixed)
    fDr = _dataRows(fixed)
    if fHc and not _isJunk(fHc) and fDr:
        return fixed, fHc, fDr
    return None


def _hzResolveStructType(sub, hc, structType):
    """structType == 'skip' 이면 stripUnitHeader 로 재분류 시도. 반환: (sub, hc, structType)."""
    from dartlab.providers.dart.docs.sections.tableParser import (
        _classifyStructure,
        _dataRows,
        _headerCells,
        _isJunk,
    )

    if structType != "skip":
        return sub, hc, structType
    fixed = stripUnitHeader(sub)
    if fixed is None:
        return sub, hc, structType
    fHc = _headerCells(fixed)
    fDr = _dataRows(fixed)
    if fHc and not _isJunk(fHc) and fDr:
        return fixed, fHc, _classifyStructure(fHc)
    return sub, hc, structType


def _hzCollectHeaderGroups(boRow, periodCols: list[str]) -> dict[str, list[str]]:
    """기간별 서브테이블 헤더 시그니처 수집. 반환: {헤더: [기간..]}."""
    from dartlab.providers.dart.docs.sections.tableParser import (
        _classifyStructure,
        _dataRows,
        _headerCells,
        _isJunk,
        splitSubtables,
    )

    groups: dict[str, list[str]] = {}
    for p in periodCols:
        md = boRow[p][0] if p in boRow.columns else None
        if md is None:
            continue
        for sub in splitSubtables(str(md)):
            hc = _headerCells(sub)
            if _isJunk(hc):
                continue
            fixed = _hzFixSubtable(sub, hc, _dataRows(sub))
            if fixed is None:
                continue
            sub, hc, _ = fixed
            structType = _classifyStructure(hc)
            _, hc, _ = _hzResolveStructType(sub, hc, structType)
            gh = _hzGroupHeader(hc)
            groups.setdefault(gh, [])
            if p not in groups[gh]:
                groups[gh].append(p)
    return groups


def _hzCollectMultiYear(sub, pYear: int, p: str, allItems, seenItems, periodItemVal) -> None:
    """multi-year 서브테이블 → (item, period, val) 수집."""
    from dartlab.providers.dart.docs.sections.tableParser import _parseMultiYear

    triples, _ = _parseMultiYear(sub, pYear)
    for rawItem, year, val in triples:
        if year != str(pYear):
            continue
        item = _hzNormalizeItem(rawItem)
        if item not in seenItems:
            allItems.append(item)
            seenItems.add(item)
        periodItemVal.setdefault(item, {})[p] = val


def _hzCollectKvMatrix(sub, p: str, allItems, seenItems, periodItemVal) -> None:
    """key-value / matrix → (item, period, val) 수집."""
    from dartlab.providers.dart.docs.sections.tableParser import _parseKeyValueOrMatrix

    rows, headerNames, _ = _parseKeyValueOrMatrix(sub)
    for rawItem, vals in rows:
        item = _hzNormalizeItem(rawItem)
        nonEmpty = [v for v in vals if v.strip()]
        if len(headerNames) >= 2 and len(nonEmpty) >= 2 and len(nonEmpty) <= len(headerNames):
            for hi, hname in enumerate(headerNames):
                v = vals[hi].strip() if hi < len(vals) else ""
                if not v or v == "-":
                    continue
                compound = f"{item}_{hname}"
                if compound not in seenItems:
                    allItems.append(compound)
                    seenItems.add(compound)
                periodItemVal.setdefault(compound, {})[p] = v
        else:
            val = " | ".join(v for v in vals if v.strip()).strip()
            if val:
                if item not in seenItems:
                    allItems.append(item)
                    seenItems.add(item)
                periodItemVal.setdefault(item, {})[p] = val


def _hzProcessPeriod(boRow, p: str, bestHeader: str, allItems, seenItems, periodItemVal) -> None:
    """단일 기간의 모든 서브테이블을 처리하여 items/values 수집."""
    from dartlab.providers.dart.docs.sections.tableParser import (
        _classifyStructure,
        _dataRows,
        _headerCells,
        _isJunk,
        splitSubtables,
    )

    md = boRow[p][0] if p in boRow.columns else None
    if md is None:
        return
    m = re.match(r"\d{4}", p)
    if m is None:
        return
    pYear = int(m.group())

    for sub in splitSubtables(str(md)):
        hc = _headerCells(sub)
        if _isJunk(hc):
            continue
        fixed = _hzFixSubtable(sub, hc, _dataRows(sub))
        if fixed is None:
            continue
        sub, hc, _ = fixed
        structType = _classifyStructure(hc)
        sub, hc, structType = _hzResolveStructType(sub, hc, structType)
        if _hzGroupHeader(hc) != bestHeader:
            continue

        if structType == "multi_year":
            beforeLen = len(allItems)
            _hzCollectMultiYear(sub, pYear, p, allItems, seenItems, periodItemVal)
            if len(allItems) == beforeLen and len(hc) >= 2:
                _hzCollectKvMatrix(sub, p, allItems, seenItems, periodItemVal)
        elif structType in ("key_value", "matrix"):
            _hzCollectKvMatrix(sub, p, allItems, seenItems, periodItemVal)


def _hzFilterJunkItems(allItems: list[str]) -> list[str]:
    """숫자만 있는 항목명 제거."""

    def isJunk(name: str) -> bool:
        """isJunk — TODO 한국어 동작 설명.

        Args:
            name: 인자.

        Raises:
            없음.

        Example:
            >>> isJunk(...)
        """
        stripped = re.sub(r"[,.\-\s]", "", name)
        return stripped.isdigit() or not stripped

    return [item for item in allItems if not isJunk(item)]


def _hzIsHistoryShape(allItems: list[str], periodItemVal: dict) -> bool:
    """이력형 감지 — 기간별 항목 overlap 이 낮으면 True (수평화 부적합)."""
    periodItemSets: dict[str, set[str]] = {}
    for item in allItems:
        for p in periodItemVal.get(item, {}):
            periodItemSets.setdefault(p, set()).add(item)
    if len(periodItemSets) < 2:
        return False
    sets = list(periodItemSets.values())
    totalOverlap = 0.0
    totalPairs = 0
    for i in range(len(sets)):
        for j in range(i + 1, min(i + 4, len(sets))):
            union = len(sets[i] | sets[j])
            inter = len(sets[i] & sets[j])
            if union > 0:
                totalOverlap += inter / union
                totalPairs += 1
    avgOverlap = totalOverlap / totalPairs if totalPairs else 0
    return avgOverlap < 0.3 and len(allItems) > 5


def _hzIsSparse(allItems: list[str], usedPeriods: list[str], periodItemVal: dict) -> bool:
    """sparse 감지 — fill rate < 0.5 면 True."""
    if not (len(usedPeriods) >= 3 and len(allItems) > 15):
        return False
    totalCells = len(allItems) * len(usedPeriods)
    if totalCells == 0:
        return False
    filled = sum(1 for item in allItems for p in usedPeriods if periodItemVal.get(item, {}).get(p))
    return filled / totalCells < 0.5


def _hzBuildDataFrame(allItems: list[str], usedPeriods: list[str], periodItemVal: dict) -> pl.DataFrame | None:
    """수집된 items/values → 항목×기간 DataFrame."""
    schema: dict[str, type] = {"항목": pl.Utf8}
    for p in usedPeriods:
        schema[p] = pl.Utf8
    rows = []
    for item in allItems:
        if not any(periodItemVal.get(item, {}).get(p) for p in usedPeriods):
            continue
        row: dict[str, str | None] = {"항목": item}
        for p in usedPeriods:
            row[p] = periodItemVal.get(item, {}).get(p)
        rows.append(row)
    return pl.DataFrame(rows, schema=schema) if rows else None


def horizontalizeTableBlock(
    topicFrame: pl.DataFrame,
    blockOrder: int,
    periodCols: list[str],
    period: str | None = None,
) -> pl.DataFrame | None:
    """table 블록을 기간 간 수평화 — 항목×기간 매트릭스 (Q3.1f split).

    Parameters
    ----------
    topicFrame : pl.DataFrame
        sections 에서 해당 topic 의 행.
    blockOrder : int
        블록 인덱스.
    periodCols : list[str]
        기간 컬럼 목록.
    period : str, optional
        특정 기간 필터 (현재 미사용).

    Returns
    -------
    pl.DataFrame | None
        항목(행) × 기간(열) DataFrame. 수평화 불가 시 None.
        "항목" : str — 행 라벨
        {period} : str — 기간별 셀 값

    Raises:
        없음.

    Example:
        >>> horizontalizeTableBlock(...)
    """
    boRow = topicFrame.filter((pl.col("blockOrder") == blockOrder) & (pl.col("blockType") == "table"))
    if boRow.is_empty():
        return None

    headerGroups = _hzCollectHeaderGroups(boRow, periodCols)
    if headerGroups:
        bestHeader = max(headerGroups, key=lambda k: len(headerGroups[k]))
        bestPeriods = set(headerGroups[bestHeader])
    else:
        bestHeader = ""
        bestPeriods = set(periodCols)

    allItems: list[str] = []
    seenItems: set[str] = set()
    periodItemVal: dict[str, dict[str, str]] = {}

    for p in periodCols:
        if p not in bestPeriods:
            continue
        _hzProcessPeriod(boRow, p, bestHeader, allItems, seenItems, periodItemVal)

    if not allItems:
        return None
    allItems = _hzFilterJunkItems(allItems)
    if not allItems:
        return None

    if _hzIsHistoryShape(allItems, periodItemVal):
        return None
    if len(allItems) > 50:
        return None

    usedPeriods = [p for p in periodCols if any(p in periodItemVal.get(item, {}) for item in allItems)]
    if not usedPeriods:
        return None
    if _hzIsSparse(allItems, usedPeriods, periodItemVal):
        return None

    return _hzBuildDataFrame(allItems, usedPeriods, periodItemVal)
