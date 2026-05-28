"""SEC iXBRL fact 시계열 horizontalize — concept × period DataFrame.

dart/parse/tableHorizontalizer 의 SEC 등가. iXBRL fact (long format) 을
horizontalized (wide) DataFrame 으로 pivot — caller 가 시계열 분석 시 직관.

본 wrapper 는 thin — context 정보 (period start/end) 활용은 별 cycle.

plan delegated-prancing-tower PR-E8 — HTML native table parse path 신규.
content_raw (filing-level iXBRL HTML) 의 ``<table>`` 을 BeautifulSoup 으로 직접
파싱해 rowspan/colspan/align 정보 native 인식. markdown 변환 단계에서 lossy 되던
표 구조 정보 회복.
"""

from __future__ import annotations

import polars as pl


def horizontalizeFacts(facts: pl.DataFrame, *, periodCol: str = "contextRef") -> pl.DataFrame:
    """iXBRL fact (long) → concept × period (wide) DataFrame.

    Args:
        facts: ``extractIxbrlFacts`` 결과 — ``concept`` / ``value`` /
            ``contextRef`` 컬럼 보유.
        periodCol: period 식별 컬럼명 (default ``"contextRef"``).

    Returns:
        wide DataFrame — 행 = concept, 열 = period (contextRef 별). 값 = value
        문자열. 빈 입력 → 빈 DataFrame.

    Raises:
        없음.

    Example:
        >>> wide = horizontalizeFacts(facts)  # doctest: +SKIP
        >>> # 컬럼: concept + 각 contextRef
    """
    if facts.is_empty():
        return facts.head(0)
    if "concept" not in facts.columns or "value" not in facts.columns:
        return facts.head(0)
    if periodCol not in facts.columns:
        return facts.head(0)
    return facts.select(["concept", periodCol, "value"]).pivot(
        on=periodCol, index="concept", values="value", aggregate_function="first"
    )


def fetchHorizontalSlice(
    facts: pl.DataFrame, concepts: list[str], *, periodCol: str = "contextRef", limit: int = 100
) -> pl.DataFrame:
    """``horizontalizeFacts`` 의 단발 + concept 필터 single-call helper.

    Args:
        facts: iXBRL fact DataFrame.
        concepts: 추출할 concept list (예 ``["us-gaap:Revenue"]``).
        periodCol: period 컬럼명.
        limit: 결과 row 수.

    Returns:
        concept × period wide DataFrame (concepts 필터 후 horizontalize).

    Raises:
        없음.

    Example:
        >>> rev = fetchHorizontalSlice(facts, ["us-gaap:Revenue"])  # doctest: +SKIP
    """
    if facts.is_empty():
        return facts.head(0)
    if "concept" not in facts.columns:
        return facts.head(0)
    filtered = facts.filter(pl.col("concept").is_in(concepts))
    if filtered.is_empty():
        return filtered
    wide = horizontalizeFacts(filtered, periodCol=periodCol)
    if limit > 0:
        wide = wide.head(limit)
    return wide


def iterHorizontalSlice(facts: pl.DataFrame, conceptGroups: list[list[str]], *, periodCol: str = "contextRef"):
    """``fetchHorizontalSlice`` 의 streaming pair (룰 10) — 그룹별 yield.

    Args:
        facts: iXBRL fact DataFrame.
        conceptGroups: concept group list (예 ``[["us-gaap:Revenue"], ["us-gaap:Assets"]]``).
        periodCol: period 컬럼명.

    Yields:
        그룹별 wide DataFrame.

    Raises:
        없음.

    Example:
        >>> for slice_ in iterHorizontalSlice(facts, [["us-gaap:Revenue"]]):
        ...     pass  # doctest: +SKIP
    """
    for concepts in conceptGroups:
        yield fetchHorizontalSlice(facts, concepts, periodCol=periodCol)


# ── PR-E8: HTML native table parser ─────────────────────────────────────────


def parseHtmlTable(html: str, *, tableIndex: int = 0) -> pl.DataFrame | None:
    """raw iXBRL HTML 의 ``<table>`` 을 native 파싱 — rowspan/colspan expansion.

    plan delegated-prancing-tower PR-E8. ``Company.sectionsRaw()`` 결과의 cell 안
    ``<table>`` 을 BeautifulSoup 으로 직접 파싱. markdown 변환 (``_tableToMarkdown``)
    이 lossy 되던 ``rowspan/colspan/align`` 정보 native 인식.

    Args:
        html: HTML 단편 (``<table>`` 포함). filing-level outerHTML 가능.
        tableIndex: 여러 ``<table>`` 중 N 번째 (0-based). out-of-range 시 None.

    Returns:
        DataFrame — 컬럼명 ``col0/col1/.../colN``, row 는 expand 후 그리드. align 속성은
        별도 metadata column ``_align``/``_rowspan``/``_colspan`` 으로 보존 안 함 (caller 가
        BeautifulSoup 재호출). 본 함수는 text 그리드 + rowspan/colspan expansion 만.

    Raises:
        없음 — 파싱 실패 시 None.

    Example:
        >>> df = parseHtmlTable('<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>')  # doctest: +SKIP
        >>> df.shape
        (2, 2)
    """
    if not html or "<table" not in html.lower():
        return None
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
    except (ImportError, ValueError):
        return None

    tables = soup.find_all("table")
    if not tables or tableIndex >= len(tables):
        return None
    table = tables[tableIndex]

    # 1 pass — 각 row 의 cell list + rowspan/colspan 메타 수집.
    parsed: list[list[tuple[str, int, int]]] = []  # row → [(text, rowspan, colspan)]
    for tr in table.find_all("tr"):
        cells: list[tuple[str, int, int]] = []
        for cell in tr.find_all(["td", "th"]):
            text = cell.get_text(" ", strip=True)
            try:
                rs = int(cell.get("rowspan", 1) or 1)
            except (TypeError, ValueError):
                rs = 1
            try:
                cs = int(cell.get("colspan", 1) or 1)
            except (TypeError, ValueError):
                cs = 1
            cells.append((text, rs, cs))
        if cells:
            parsed.append(cells)

    if not parsed:
        return None

    # 2 pass — rowspan/colspan expansion. 2D grid 채우기.
    grid: list[list[str]] = []
    occupied: dict[tuple[int, int], bool] = {}
    for rIdx, rowCells in enumerate(parsed):
        while len(grid) <= rIdx:
            grid.append([])
        cIdx = 0
        for text, rs, cs in rowCells:
            # 점유된 cell 건너뛰기 (이전 row 의 rowspan 흔적).
            while occupied.get((rIdx, cIdx), False):
                cIdx += 1
            # text 채우기 + rowspan/colspan 영역 점유.
            for dr in range(rs):
                for dc in range(cs):
                    rr, cc = rIdx + dr, cIdx + dc
                    while len(grid) <= rr:
                        grid.append([])
                    while len(grid[rr]) <= cc:
                        grid[rr].append("")
                    if dr == 0 and dc == 0:
                        grid[rr][cc] = text
                    else:
                        # rowspan/colspan 영역 - 같은 text 반복 (분석 path 가 빈 값으로 처리 가능).
                        grid[rr][cc] = text
                    occupied[(rr, cc)] = True
            cIdx += cs

    # 3 pass — DataFrame 변환. 컬럼명 col0..colN (max col 수 기준).
    maxCols = max((len(r) for r in grid), default=0)
    if maxCols == 0:
        return None
    normalized = [r + [""] * (maxCols - len(r)) for r in grid]
    columns = [f"col{i}" for i in range(maxCols)]
    return pl.DataFrame(normalized, schema=columns, orient="row")


def parseHtmlTables(html: str) -> list[pl.DataFrame]:
    """raw HTML 의 모든 ``<table>`` 을 순서대로 native 파싱.

    Args:
        html: HTML 단편 (filing-level outerHTML 가능).

    Returns:
        ``parseHtmlTable`` 결과 list. ``<table>`` 0 개면 빈 list.

    Raises:
        없음.

    Example:
        >>> tables = parseHtmlTables(rawHtml)  # doctest: +SKIP
    """
    if not html or "<table" not in html.lower():
        return []
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
    except (ImportError, ValueError):
        return []
    nTables = len(soup.find_all("table"))
    results: list[pl.DataFrame] = []
    for i in range(nTables):
        df = parseHtmlTable(html, tableIndex=i)
        if df is not None:
            results.append(df)
    return results
