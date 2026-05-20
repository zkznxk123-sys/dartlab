"""테이블 파서 — sections의 markdown 테이블을 구조화된 DataFrame으로 변환.

구조 타입별 병합 전략:
- multi_year: 당기/전기/전전기 → 기수→연도 변환 → 체인 브릿지 수평화
- key_value: 2컬럼 키-값 → 기간별 단순 수평화
- matrix: 3컬럼+ → 첫 컬럼=항목, 나머지=값, 기간별 수평화
"""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict

import polars as pl

# 표 cell 정규화 — period-variable meta 제거 → 같은 의미 표가 같은 hash.
# 회귀 사례 (000660 companyOverview): "(기준일: 2025년 12월 31일)" / "(단위 : 사)"
# 같은 meta row 가 매 period 마다 변동되어 hash 분리 → 13 개 row 분산 → wide-format
# pivot 의미 무너짐. 정규화로 meta 무시 후 hash → 같은 row 정합.
_RE_META_DATE = re.compile(r"\(\s*(?:기준일|작성기준일|보고기준일|평가일|평가기준일)[^)]*\)")
_RE_META_UNIT = re.compile(r"\(\s*단위\s*:\s*[^)]+\)")
_RE_META_YEAR = re.compile(r"\d{4}(?:년(?:\s*(?:상반기|하반기|\d+\s*분기))?|Q\d|\.\d{1,2})?")
# "제 N기 N분기" / "제 N기 반기" / "제 N기" — period-variable. 다 함께 strip.
_RE_META_KISU = re.compile(r"제\s*\d+\s*기(?:\s*\d+\s*분기|\s*반기|\s*\d+\s*기)?")
_RE_META_DATE_FRAGMENT = re.compile(r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일")


def _normalizeHashCell(cell: str) -> str:
    """cell 안 period-variable meta (기준일/단위/연도/기수) 제거 후 lowercase + whitespace strip."""
    c = _RE_META_DATE.sub("", cell)
    c = _RE_META_UNIT.sub("", c)
    c = _RE_META_DATE_FRAGMENT.sub("", c)
    c = _RE_META_YEAR.sub("", c)
    c = _RE_META_KISU.sub("", c)
    c = re.sub(r"\s+", " ", c).strip().lower()
    return c


_RE_SENTENCE_ENDING = re.compile(r"(?:니다|입니다|같습니다|있습니다|없습니다|됩니다|합니다)\.?\s*$")


def tableHeaderHash(md: str) -> str:
    """markdown 표의 *real header row* (period-variable meta + intro 문 제외) cells 의 안정 hash.

    옛/최근 보고서의 *다른 의미* 표가 sourceBlockOrder 위치만 같다고 같은 segmentKey
    받는 회귀 차단용. 진짜 column header row 추출:
    - separator row (---) skip
    - meta-only row (기준일/단위/연도) skip
    - **intro 문 row** ("...같습니다.", "...입니다." 류 종결사 sentence) skip — period 별
      변동되는 본문 sentence 가 첫 row 인 경우 차단
    - 첫 진짜 header (column names) 의 cells 정규화 + sorted → blake2b 4-byte hex.

    Args:
        md: markdown 표 본문.

    Returns:
        str — 8 글자 hex hash. 진짜 header row 없으면 ``"empty"``.
    """
    for line in md.strip().split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [_normalizeHashCell(c) for c in stripped.strip("|").split("|")]
        # separator row skip
        if all(set(c) <= {"-", ":"} for c in cells if c):
            continue
        nonEmpty = [c for c in cells if c]
        if not nonEmpty:
            continue
        # intro 문 row skip — 본문 sentence 가 첫 row 인 경우. 종결사 매칭 시 next row.
        if any(_RE_SENTENCE_ENDING.search(c) for c in nonEmpty):
            continue
        norm = tuple(sorted(nonEmpty))
        return hashlib.blake2b(str(norm).encode("utf-8"), digest_size=4).hexdigest()
    return "empty"


# ── 서브테이블 분리 ──


def splitSubtables(md: str) -> list[list[str]]:
    """구분선 기준 서브테이블 분리.

    Args:
        md: 인자.

    Raises:
        없음.

    Example:
        >>> splitSubtables(...)

    Returns:
        list[list[str]] — 서브테이블 라인 리스트.

    SeeAlso:
        - ``analysis`` / ``extractors`` — sections table 호출자.

    Requires:
        - polars

    Capabilities:
        - sections markdown table → 구조 분류 + 수평화 + 서브테이블 분리.

    Guide:
        - 사용자 API 는 ``c.table()`` — 본 모듈 직접 호출 X.

    AIContext:
        internal table parser — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections analysis 위임.
        OutputSchema:
            - pl.DataFrame / list / dict — 함수별.
        Prerequisites:
            - sections 본문 markdown.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - markdown table → 구조 분류 → 수평화 DataFrame.
        TargetMarkets:
            - KR (DART) sections table parser.
    """
    tables: list[list[str]] = []
    current: list[str] = []

    for line in md.strip().split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            if current:
                tables.append(current)
                current = []
            continue

        cells = [c.strip() for c in s.strip("|").split("|")]
        isSep = all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip())

        if isSep and current:
            if len(current) >= 2:
                prev = current[:-1]
                if prev:
                    tables.append(prev)
                current = [current[-1], s]
            else:
                current.append(s)
        else:
            current.append(s)

    if current:
        tables.append(current)
    return tables


# ── 유틸 ──


def _headerCells(lines: list[str]) -> list[str]:
    for line in lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            return [c for c in cells if c.strip()]
    return []


def _dataRows(lines: list[str]) -> list[list[str]]:
    rows = []
    sepDone = False
    for line in lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            sepDone = True
            continue
        if sepDone:
            rows.append(cells)
    return rows


def _normalizeHeader(headerCells: list[str]) -> str:
    h = " | ".join(headerCells)
    h = re.sub(r"\d{4}(Q\d)?", "", h)
    h = re.sub(r"제\s*\d+\s*기", "", h)
    h = re.sub(r"\(\s*단위\s*:\s*[^)]+\)", "", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


def _normalizeItemName(name: str) -> str:
    n = re.sub(r"\s+", "", name)
    n = n.replace("（", "(").replace("）", ")")
    n = n.replace("ㆍ", "·")
    return n


def _isJunk(headerCells: list[str]) -> bool:
    if not headerCells:
        return True
    h = " ".join(headerCells).strip()
    if not h or set(h) <= {"|", " "}:
        return True
    if h.startswith("※") or h.startswith("☞") or h.startswith("[△"):
        return True
    if "본문 위치로 이동" in h:
        return True
    if len(h) < 5:
        return True
    return False


def _extractUnit(lines: list[str]) -> str | None:
    full = "\n".join(lines)
    m = re.search(r"\(\s*단위\s*:\s*([^)]+)\)", full)
    return m.group(1).strip() if m else None


# ── 구조 분류 ──

_MULTI_YEAR_KW = {"당기", "전기", "전전기", "당반기", "전반기"}
_STOCK_TYPES = {"보통주", "우선주", "기타주식"}


def _classifyStructure(headerCells: list[str]) -> str:
    joined = " ".join(headerCells)
    if any(kw in joined for kw in _MULTI_YEAR_KW):
        return "multi_year"
    if len(headerCells) == 2:
        return "key_value"
    if len(headerCells) >= 3:
        return "matrix"
    return "skip"


# ── multi_year 파싱 ──


def _parseMultiYear(sub: list[str], periodYear: int) -> tuple[list[tuple[str, str, str]], str | None]:
    """multi_year → [(항목, 연도, 값), ...] + 단위."""
    sepIdx = -1
    for i, line in enumerate(sub):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            sepIdx = i
            break

    if sepIdx < 0 or sepIdx + 1 >= len(sub):
        return [], None

    # 기수 행
    kisuCells = [c.strip() for c in sub[sepIdx + 1].strip("|").split("|")]
    kisuNums = []
    for cell in kisuCells:
        m = re.search(r"제\s*(\d+)\s*기", cell)
        if m:
            kisuNums.append(int(m.group(1)))

    if not kisuNums:
        return [], None

    maxKisu = max(kisuNums)
    sortedKisu = sorted(kisuNums, reverse=True)
    kisuToYear = {kn: str(periodYear - maxKisu + kn) for kn in kisuNums}

    unit = _extractUnit(sub)
    triples: list[tuple[str, str, str]] = []
    prevItem = ""

    for line in sub[sepIdx + 2 :]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c.strip()) <= {"-", ":"} for c in cells if c.strip()):
            continue
        if not cells:
            continue
        if not cells[0].strip():
            if not prevItem:
                continue
            first = prevItem
        else:
            first = cells[0].strip()

        if first.startswith("※"):
            continue

        # 보통주/우선주 연속행
        if first in _STOCK_TYPES and prevItem:
            itemName = _normalizeItemName(f"{prevItem}-{first}")
            valCells = cells[1:]
        elif len(cells) > 1 and cells[1].strip() in _STOCK_TYPES:
            stockType = cells[1].strip()
            itemName = _normalizeItemName(f"{first}-{stockType}")
            valCells = cells[2:]
            prevItem = first
        else:
            itemName = _normalizeItemName(first)
            valCells = cells[1:]
            prevItem = first

        for i, kn in enumerate(sortedKisu):
            if i < len(valCells):
                val = valCells[i].strip()
                if val and val != "-" and val not in _STOCK_TYPES:
                    triples.append((itemName, kisuToYear[kn], val))

    return triples, unit


# ── key_value / matrix 파싱 ──


def _parseKeyValueOrMatrix(sub: list[str]) -> tuple[list[tuple[str, list[str]]], list[str], str | None]:
    """key_value/matrix → [(항목, [값1, 값2, ...]), ...] + 헤더컬럼명 + 단위.

    다중행 헤더, 그룹 헤더, 주석 행 처리 포함.
    """
    headerCells = _headerCells(sub)
    headerNames = [_normalizeItemName(h) for h in headerCells[1:]] if len(headerCells) > 1 else []
    rows = _dataRows(sub)
    unit = _extractUnit(sub)
    result: list[tuple[str, list[str]]] = []

    if not rows:
        return result, headerNames, unit

    # 다중행 헤더 감지: 첫 데이터행이 순수 텍스트(숫자 없음)이고 컬럼 수가 헤더와 비슷하면 서브헤더
    firstRow = rows[0]
    isSubHeader = (
        len(firstRow) >= len(headerCells)
        and all(not any(ch.isdigit() for ch in cell) or not cell.strip() for cell in firstRow)
        and len(rows) > 1
    )
    dataStart = 1 if isSubHeader else 0

    prevGroupItem = ""
    prevCarryItem = ""
    for row in rows[dataStart:]:
        if not row:
            continue
        if not row[0].strip():
            if not prevCarryItem:
                continue
            first = prevCarryItem
        else:
            first = row[0].strip()
        if first.startswith("※") or first.startswith("☞"):
            continue

        item = _normalizeItemName(first)
        values = [c.strip() for c in row[1:]]

        # 그룹 헤더 감지: 값이 전부 비어있거나 1개만 있고 다음 행들이 세부 항목
        allEmpty = all(not v or v == "-" for v in values)
        if allEmpty and len(values) >= 2:
            prevGroupItem = item
            continue

        # 그룹 헤더 하위 항목이면 접두사 추가
        if prevGroupItem and not allEmpty:
            item = f"{prevGroupItem}_{item}"

        if item:
            result.append((item, values))
            prevCarryItem = first

    return result, headerNames, unit


# ── 통합 빌더 ──


def buildTableDataFrame(
    topicFrame: pl.DataFrame,
    periodCols: list[str],
) -> pl.DataFrame | None:
    """sections의 table 행 → 수평화된 DataFrame.

    구조 타입별로 다른 병합 전략 적용.

    Args:
        topicFrame: 인자.
        periodCols: 인자.

    Raises:
        없음.

    Example:
        >>> buildTableDataFrame(...)

    Returns:
        pl.DataFrame 또는 None — 수평화 결과.

    SeeAlso:
        - ``analysis`` / ``extractors`` — sections table 호출자.

    Requires:
        - polars

    Capabilities:
        - sections markdown table → 구조 분류 + 수평화 + 서브테이블 분리.

    Guide:
        - 사용자 API 는 ``c.table()`` — 본 모듈 직접 호출 X.

    AIContext:
        internal table parser — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 본 모듈 직접 호출 X — sections analysis 위임.
        OutputSchema:
            - pl.DataFrame / list / dict — 함수별.
        Prerequisites:
            - sections 본문 markdown.
        Freshness:
            - docs 갱신 시점.
        Dataflow:
            - markdown table → 구조 분류 → 수평화 DataFrame.
        TargetMarkets:
            - KR (DART) sections table parser.
    """
    if topicFrame.is_empty():
        return None

    # key: (blockOrder, normHeader) → {period → [(항목,값)]} / [(항목,연도,값)]
    kvData: dict[tuple[int, str], dict[str, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    myData: dict[tuple[int, str], list[tuple[str, str, str]]] = defaultdict(list)
    units: dict[tuple[int, str], str] = {}

    for record in topicFrame.iter_rows(named=True):
        blockOrder = int(record.get("blockOrder") or 0)
        for p in periodCols:
            if p not in topicFrame.columns:
                continue
            md = record.get(p)
            if md is None:
                continue

            pYear = int(re.match(r"\d{4}", p).group()) if re.match(r"\d{4}", p) else None

            for sub in splitSubtables(str(md)):
                hc = _headerCells(sub)
                if _isJunk(hc):
                    continue

                # 0행 서브테이블 스킵 (단위, 주석, 기준일 등)
                dr = _dataRows(sub)
                if not dr:
                    continue

                normH = _normalizeHeader(hc)
                groupKey = (blockOrder, normH)
                structType = _classifyStructure(hc)

                if structType == "multi_year" and pYear and "Q" not in p:
                    triples, unit = _parseMultiYear(sub, pYear)
                    myData[groupKey].extend(triples)
                    if unit:
                        units[groupKey] = unit

                elif structType in ("key_value", "matrix"):
                    rows, headerNames, unit = _parseKeyValueOrMatrix(sub)
                    if unit:
                        units[groupKey] = unit

                    # key_value/matrix: 첫 컬럼=항목, 나머지=값 (파이프로 합침)
                    for item, vals in rows:
                        val = " | ".join(v for v in vals if v).strip()
                        if val:
                            kvData[groupKey][p].append((item, val))

    if not kvData and not myData:
        return None

    outRows: list[dict[str, str | None]] = []

    # multi_year → 항목 × 연도
    for (blockOrder, normH), triples in myData.items():
        allItems: list[str] = []
        seenItems: set[str] = set()
        yearItemVal: dict[str, dict[str, str]] = defaultdict(dict)

        for item, year, val in triples:
            if item not in seenItems:
                allItems.append(item)
                seenItems.add(item)
            yearItemVal[item][year] = val

        allYears = sorted(set(y for iv in yearItemVal.values() for y in iv.keys()))
        unit = units.get((blockOrder, normH), "")

        subtableName = normH[:50] if normH else ""

        for item in allItems:
            row: dict[str, str | None] = {
                "blockType": "table",
                "blockOrder": blockOrder,
                "tableType": "multi_year",
                "subtable": subtableName,
                "단위": unit,
                "항목": item,
                "_rowOrder": len(outRows),
            }
            for y in allYears:
                row[y] = yearItemVal[item].get(y)
            outRows.append(row)

    # key_value / matrix → 항목 × period
    for (blockOrder, normH), periodData in kvData.items():
        allItems: list[str] = []
        seenItems: set[str] = set()
        periodItemVal: dict[str, dict[str, str]] = defaultdict(dict)

        for p, pairs in periodData.items():
            for item, val in pairs:
                if item not in seenItems:
                    allItems.append(item)
                    seenItems.add(item)
                periodItemVal[item][p] = val

        unit = units.get((blockOrder, normH), "")

        # normHeader에서 사람 읽기용 subtable명 생성
        subtableName = normH[:50] if normH else ""

        for item in allItems:
            row: dict[str, str | None] = {
                "blockType": "table",
                "blockOrder": blockOrder,
                "tableType": "key_value",
                "subtable": subtableName,
                "단위": unit,
                "항목": item,
                "_rowOrder": len(outRows),
            }
            for p in periodCols:
                row[p] = periodItemVal[item].get(p)
            outRows.append(row)

    if not outRows:
        return None

    # 각 normHeader 그룹별로 DataFrame 생성 후 concat
    # (다른 서브테이블은 다른 컬럼 세트를 가질 수 있으므로)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in outRows:
        # tableType + 항목 세트로 그룹핑
        key = row.get("tableType", "unknown")
        groups[key].append(row)

    frames: list[pl.DataFrame] = []
    for key, rows in groups.items():
        try:
            frames.append(pl.DataFrame(rows))
        except (pl.exceptions.SchemaError, pl.exceptions.ComputeError, ValueError):
            import logging

            logging.getLogger(__name__).debug("tableParser group schema mismatch: %s", key, exc_info=True)
            # 같은 tableType 내에서도 스키마 다를 수 있음 → 개별 처리
            for row in rows:
                try:
                    frames.append(pl.DataFrame([row]))
                except (pl.exceptions.SchemaError, pl.exceptions.ComputeError, ValueError):
                    pass

    if not frames:
        return None
    if len(frames) == 1:
        return frames[0]
    return pl.concat(frames, how="diagonal_relaxed")
