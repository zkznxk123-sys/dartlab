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
    """단위행/기준일행 헤더 서브테이블 → 실제 헤더부터 잘라낸 list 반환.

    Capabilities:
        - DART 공시 표의 첫 행이 "(단위:천원)" 또는 "(기준일 : YYYY년 MM월 DD일)" 같은
          메타 라벨일 때, 이 메타 행을 제거하고 실 헤더부터 시작하는 markdown table
          서브셋 반환.
        - 다중 컬럼 패턴 ("| (기준일 : | 2018-03-31 | ) | (단위 : 주) |") 도 처리.
        - 메타 행 없으면 None 반환 (기존 파서가 그대로 사용).

    Args:
        sub: markdown table 의 라인 list. 각 라인은 ``"| col1 | col2 |"`` 형식.

    Returns:
        list[str] | None — 메타 헤더 제거 후 실 헤더부터 시작하는 라인 list. 메타 헤더가
        없거나 separator 패턴이 부적합하면 None. separator (``---``) 부재면 자동 생성.

    Example:
        >>> sub = [
        ...     "| (단위:천원) |",
        ...     "| --- |",
        ...     "| 자산총계 |",
        ...     "| --- |",
        ...     "| 100 |",
        ... ]
        >>> stripUnitHeader(sub)  # doctest: +ELLIPSIS
        ['| 자산총계 |', ...]

    Guide:
        - "공시 표 단위 행 자동 제거" → 본 함수 호출 후 ``horizontalizeTableBlock`` 입력.
        - 단위/기준일 메타가 없는 표 → None 반환, caller 가 sub 원본 그대로 사용.

    SeeAlso:
        - ``horizontalizeTableBlock`` — 본 함수 결과를 받아 행/열 매트릭스화하는 후속.
        - ``_UNIT_ONLY_RE`` / ``_DATE_ONLY_RE`` — 메타 헤더 패턴 정규식.

    Requires:
        - re — 메타 헤더 패턴 매칭.
        - 외부 의존성 없음 (pure string manipulation).

    AIContext:
        DART 공시 본문 → sections 파싱 파이프라인의 전처리 단계. table block parser 가
        본 함수를 호출해 메타 행 영향 받지 않는 깨끗한 헤더 받음. Ask Workbench 의
        finance topic 추출 시 background.

    LLM Specifications:
        AntiPatterns:
            - 빈 list 입력 → None (FirstRow 식별 실패).
            - separator (``|--|``) 가 모든 행에서 부재 → None (table 형식 아님).
            - 메타 라벨이 본문 중간에 있으면 미감지 (첫 데이터 행만 검사).
        OutputSchema:
            - list[str] — markdown table 라인 (헤더 + separator + 데이터).
            - None — 메타 헤더 부재 또는 형식 부적합.
        Prerequisites:
            - sub 는 이미 cell-split 가능한 markdown table 형식.
        Freshness:
            - pure function — 입력만 의존, freshness 무관.
        Dataflow:
            - DART 공시 HTML → table block split → 본 함수 → horizontalizeTableBlock.
        TargetMarkets:
            - KR (DART 공시 표). EDGAR 10-K table 은 별도 ``providers/edgar/parse``.

    Raises:
        없음.
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
    from dartlab.providers.dart.tableParser import _normalizeHeader

    h = _normalizeHeader(hc)
    h = _HZ_PERIOD_KW_RE.sub("", h)
    h = re.sub(r"\| *\|", "|", h)
    return re.sub(r"\s+", " ", h).strip()


def _hzFixSubtable(sub, hc, dr):
    """dr 비어 있으면 stripUnitHeader 로 재파싱. 반환: (sub, hc, dr) or None (불가)."""
    from dartlab.providers.dart.tableParser import (
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
    from dartlab.providers.dart.tableParser import (
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
    from dartlab.providers.dart.tableParser import (
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
    from dartlab.providers.dart.tableParser import _parseMultiYear

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
    from dartlab.providers.dart.tableParser import _parseKeyValueOrMatrix

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


def _htmlTablesToMarkdownSubtables(content: str) -> list[list[str]]:
    """HTML ``<table>`` block → markdown subtable line list (splitSubtables 호환 양식).

    plan snazzy-wibbling-origami PR-5c. mixed format cell value 가 HTML ``<table>``
    포함 시 htmlTableParser.cellGrid 로 rowspan/colspan 펼친 grid 추출 → markdown
    pipe-format subtable lines 으로 변환. ``_classifyStructure`` / ``_headerCells`` /
    ``_dataRows`` 가 처리할 수 있는 양식. ALIGN 등 시각 속성은 plain text 양식 으로 평탄화
    (수평화 path 는 값만 사용 — viewer 전용 속성 무관).

    Args:
        content: cell value (HTML ``<table>`` 1+ block 포함 가능, 다른 텍스트 혼합 OK).

    Returns:
        list[list[str]] — 각 element 는 한 subtable 의 markdown line list:
            ``["| h1 | h2 |", "| --- | --- |", "| v1 | v2 |", ...]``. 표 없으면 빈 list.

    Example:
        >>> html = '<table><tr><th>구분</th><th>금액</th></tr><tr><td>매출</td><td>100</td></tr></table>'
        >>> _htmlTablesToMarkdownSubtables(html)
        [['| 구분 | 금액 |', '| --- | --- |', '| 매출 | 100 |']]
    """
    if not content or "<table" not in content.lower():
        return []
    from dartlab.providers.dart.parse.htmlTableParser import parseHtmlTable

    out: list[list[str]] = []
    # 다중 <table> 분리 — 단순 split (lxml 가 첫 표만 반환하므로 직접 분할 필요).
    table_re = re.compile(r"<table[\s\S]*?</table>", re.IGNORECASE)
    for match in table_re.findall(content):
        parsed = parseHtmlTable(match)
        if parsed is None or not parsed.rows:
            continue
        lines: list[str] = []
        # header row 들 (multi-row header 첫 N row)
        headerRows = parsed.rows[: parsed.headerRowCount] if parsed.headerRowCount > 0 else parsed.rows[:1]
        dataRows = parsed.rows[parsed.headerRowCount :] if parsed.headerRowCount > 0 else parsed.rows[1:]
        # 첫 header row 만 markdown header 로 (multi-row header 는 합쳐 한 줄로)
        if headerRows:
            firstHeader = headerRows[0]
            cells = []
            for c in firstHeader.cells:
                cells.extend([c.text] * max(1, c.colspan))
            if cells:
                lines.append("| " + " | ".join(cells) + " |")
                lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
        for row in dataRows:
            cells = []
            for c in row.cells:
                cells.extend([c.text] * max(1, c.colspan))
            if cells:
                lines.append("| " + " | ".join(cells) + " |")
        if lines:
            out.append(lines)
    return out


def _hzProcessPeriod(boRow, p: str, bestHeader: str, allItems, seenItems, periodItemVal) -> None:
    """단일 기간의 모든 서브테이블을 처리하여 items/values 수집.

    plan snazzy-wibbling-origami PR-5c — mixed format cell 의 HTML ``<table>`` block 도
    인식. markdown pipe-format subtable 외 HTML subtable 도 ``_htmlTablesToMarkdownSubtables``
    경유로 변환 후 같은 path. ALIGN/rowspan/colspan 보존 (rowspan/colspan 펼친 grid).
    """
    from dartlab.providers.dart.tableParser import (
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

    # 옛 markdown pipe-format subtable + 신 HTML <table> subtable 통합 iter.
    contentStr = str(md)
    subtables = list(splitSubtables(contentStr))
    subtables.extend(_htmlTablesToMarkdownSubtables(contentStr))

    for sub in subtables:
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
        """숫자/구두점/공백만 남는 항목명 (실제 의미 없는 noise) 판정.

        Args:
            name: 항목명 후보.

        Returns:
            의미 없는 noise (숫자만 또는 빈 문자열) 면 True.

        Raises:
            없음.

        Example:
            >>> isJunk("12,345")
            True
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
    """table 블록을 기간 간 수평화 — 항목 × 기간 매트릭스 (Q3.1f split).

    Capabilities:
        - sections topic 의 동일 blockOrder table 들을 기간별로 모아 항목 (행) ×
          기간 (열) DataFrame 으로 정규화.
        - 헤더 그룹 (사업부문 등) 자동 감지 — 가장 많은 period 를 가진 헤더를 선택해
          노이즈 헤더 (단일 기간 부수 표) 제거.
        - junk item 필터 (단위 행, 단일 라벨 등) + history shape (시계열 단순 나열) +
          sparse (50% 미만 채움) 케이스는 None 반환 — 노이즈 표 차단.

    Args:
        topicFrame: 해당 topic 의 sections row (각 행은 한 기간의 table block).
            ``blockOrder``, ``blockType``, ``periodCols`` 컬럼 필수.
        blockOrder: table block 인덱스 (같은 topic 안 여러 block 구분).
        periodCols: 처리할 기간 컬럼 list (예 ``["2024Q1", "2024Q2", "2024Q3"]``).
        period: 특정 기간 한정 필터. 현재 미사용 — 호환성 보존 인자.

    Returns:
        pl.DataFrame | None — 행: ``항목`` (str, 라벨) + 각 기간 컬럼 (str, 셀 값).
        수평화 불가 (item 0 / history shape / sparse / >50 items) 시 None.

    Example:
        >>> import polars as pl
        >>> # 실 호출은 topicFrame schema 가 복잡 — sections 빌더 통한 간접 호출.
        >>> # 단순 빈 DataFrame 케이스:
        >>> df = pl.DataFrame({"blockOrder": [], "blockType": []})
        >>> horizontalizeTableBlock(df, 0, ["2024Q1"]) is None
        True

    Guide:
        - "공시 표를 항목 × 기간 매트릭스로" → 본 함수가 본체 (Company.show("BS") 가 내부 사용).
        - 시계열 1 행 표 (history shape) 는 자동 거부 — caller 가 다른 파서 시도.
        - DataFrame 반환 시 캐스팅 ``.with_columns(pl.col("항목").cast(pl.Utf8))`` 권장.

    SeeAlso:
        - ``stripUnitHeader`` — 사전 메타 헤더 제거.
        - ``_hzCollectHeaderGroups`` / ``_hzProcessPeriod`` / ``_hzBuildDataFrame`` —
          내부 단계 헬퍼.
        - ``_hzFilterJunkItems`` / ``_hzIsSparse`` / ``_hzIsHistoryShape`` — 노이즈 가드.

    Requires:
        - polars — DataFrame 입출력.
        - re (모듈 상수 정규식).

    AIContext:
        ``Company.show("IS")`` / ``c.show("BS")`` 가 내부 사용. evidence 로 반환 시
        ``항목`` 컬럼 + 가장 최근 period 컬럼 head 5 가 표준. None 반환 시 caller 는
        topic-level 패널 (sections row 자체) 로 fallback.

    LLM Specifications:
        AntiPatterns:
            - periodCols 가 빈 list → bestPeriods 빈 set → ``allItems`` 0 → None.
            - topicFrame 에 ``blockType`` 컬럼 부재 → 본문이 빈 DataFrame 필터 결과 →
              None.
            - 50 items 초과 표 → None (보고서 부속 표일 가능성).
        OutputSchema:
            - row: 항목 1 개 (단일 라벨 또는 정규화된 item).
            - column: ``항목`` (pl.Utf8) + periodCols 각 (pl.Utf8 — 셀 값 raw).
            - 정렬: 입력 순서 (allItems 의 등장 순).
        Prerequisites:
            - topicFrame 이 동일 topic 의 여러 period 행 묶음.
        Freshness:
            - pure function (DataFrame 변환만). 입력 freshness 에 의존.
        Dataflow:
            - sections (provider builder) → topicFrame → 본 함수 → Company.show.
        TargetMarkets:
            - KR (DART 공시 표 markdown). EDGAR 10-K 표는 별도.

    Raises:
        없음.
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
