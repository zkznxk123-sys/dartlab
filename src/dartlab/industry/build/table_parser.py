"""마크다운 테이블 범용 파서 — docs section_content에서 표 추출.

DART 공시의 section_content는 마크다운 형식의 텍스트다.
`| cell | cell |` 패턴으로 테이블을 파싱한다.

특징:
- 여러 테이블이 한 섹션에 나올 수 있음
- 헤더가 여러 줄에 걸칠 수 있음 (multi-row header)
- 빈 셀 많음, 소계/총계 행 포함
- 셀 병합 시 공백이 이어짐
"""

from __future__ import annotations

import re


def _splitTableRow(line: str) -> list[str] | None:
    """'| a | b | c |' 한 줄을 셀 리스트로 분리. 테이블 행이 아니면 None."""
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    # 맨 앞/뒤 | 제거 후 split
    cells = [c.strip() for c in line[1:-1].split("|")]
    return cells


def _isSeparatorRow(cells: list[str]) -> bool:
    """`| --- | --- |` 같은 구분선 행인지."""
    return all(re.fullmatch(r"-+", c) or c == "" for c in cells) and any(
        "-" in c for c in cells
    )


def extractTables(content: str) -> list[list[list[str]]]:
    """마크다운 텍스트에서 모든 테이블을 추출.

    Returns
    -------
    list[list[list[str]]]
        테이블 리스트. 각 테이블은 행(list) × 셀(str).
        구분선 행(---)은 제거됨.
    """
    if not content:
        return []

    tables: list[list[list[str]]] = []
    current: list[list[str]] = []

    for line in content.split("\n"):
        cells = _splitTableRow(line)
        if cells is None:
            # 테이블 종료
            if current:
                tables.append(current)
                current = []
            continue

        if _isSeparatorRow(cells):
            continue  # 구분선은 skip

        current.append(cells)

    if current:
        tables.append(current)

    # 1행짜리 노이즈 제거
    return [t for t in tables if len(t) >= 2]


def tableToRowDicts(table: list[list[str]]) -> list[dict[str, str]]:
    """테이블을 헤더 기반 dict 리스트로 변환.

    첫 번째 행을 헤더로 간주. 이전 행 값이 빈 셀은 상속(병합 효과).

    Returns
    -------
    list[dict[str, str]]
        각 row = {header: value}
    """
    if not table or len(table) < 2:
        return []

    header = table[0]
    rows: list[dict[str, str]] = []
    prev: list[str] = ["" for _ in header]

    for raw in table[1:]:
        # 열 수 맞추기
        padded = raw[: len(header)] + [""] * (len(header) - len(raw))
        # 빈 셀은 이전 값 상속 (병합 셀 처리)
        row = []
        for i, v in enumerate(padded):
            if v:
                row.append(v)
                prev[i] = v
            else:
                row.append(prev[i])
        rows.append(dict(zip(header, row)))

    return rows


def findTableByHeaders(
    tables: list[list[list[str]]],
    requiredHeaders: list[str],
    maxHeaderRows: int = 3,
) -> tuple[list[list[str]], int] | None:
    """헤더에 특정 키워드가 모두 포함된 테이블을 찾는다.

    "(단위: 억원)" 같은 메타 행이 첫 줄에 올 수 있으므로 상위 maxHeaderRows까지 탐색.

    Parameters
    ----------
    tables : list of tables
        extractTables 결과.
    requiredHeaders : list[str]
        헤더에 포함되어야 하는 키워드. 부분 매칭.
    maxHeaderRows : int
        어느 행까지 헤더로 시도할지.

    Returns
    -------
    tuple[list[list[str]], int] | None
        (매칭된 테이블, 실제 헤더 행 인덱스).
    """
    for table in tables:
        if not table:
            continue
        limit = min(maxHeaderRows, len(table))
        for hi in range(limit):
            headerText = " ".join(table[hi]).lower()
            if all(kw.lower() in headerText for kw in requiredHeaders):
                return table, hi
    return None


def tableToRowDictsWithHeaderRow(
    table: list[list[str]],
    headerRow: int = 0,
    *,
    inheritColumns: list[str] | None = None,
) -> list[dict[str, str]]:
    """특정 행을 헤더로 지정하여 dict 리스트 변환.

    Parameters
    ----------
    inheritColumns : list[str] | None
        빈 셀을 이전 행에서 상속할 헤더 키워드 목록.
        예: ['부문', '부 문'] — 병합된 셀 복원.
        None이면 상속 없음 (빈 셀은 빈 셀 그대로).
    """
    if not table or headerRow >= len(table):
        return []
    header = table[headerRow]

    # 상속할 컬럼 인덱스 결정
    inheritIdxs: set[int] = set()
    if inheritColumns:
        for i, h in enumerate(header):
            hClean = h.strip()
            if any(kw in hClean for kw in inheritColumns):
                inheritIdxs.add(i)

    rows: list[dict[str, str]] = []
    prev: list[str] = ["" for _ in header]
    # 첫 컬럼이 상속 대상일 때, 값이 비어있으면 앞 행 상속 + 나머지 칸 한 칸 당기기
    # (마크다운 테이블 rowspan 병합 효과 복원)
    shouldShift = 0 in inheritIdxs

    for raw in table[headerRow + 1 :]:
        padded = raw[: len(header)] + [""] * (len(header) - len(raw))

        # shift 필요한지 판단: 첫 셀이 비어있고 끝 셀도 비어있으면 한 칸 밀린 것
        if shouldShift and padded[0] and not padded[-1]:
            # 첫 셀이 있지만 실제로는 이전 부문의 하위 품목인지 판단
            # 조건: 끝 셀이 빈 문자열이고 첫 셀 값이 header[1]류일 때
            # 보수적: 첫 셀이 부문 값 패턴(이전 prev[0]과 같은 레벨)이 아닐 때만 shift
            # 간단한 휴리스틱: 첫 셀이 "부문"/"소계"/"총계"/"기타"가 아니고 prev[0]이 있으면 shift
            firstCell = padded[0]
            isNewBumun = any(k in firstCell for k in ["부문", "부 문", "소 계", "소계", "총 계", "총계", "기타"])
            isHarmonSam = firstCell in ["Harman", "SDC", "DX", "DS"] or firstCell.startswith("DS") or firstCell.startswith("DX")
            if not isNewBumun and not isHarmonSam and prev[0]:
                # 한 칸 당기기: [a,b,c,d,e,''] → ['', a, b, c, d, e]
                padded = [""] + padded[:-1]

        row = []
        for i, v in enumerate(padded):
            if v:
                row.append(v)
                prev[i] = v
            elif i in inheritIdxs:
                row.append(prev[i])
            else:
                row.append("")
        rows.append(dict(zip(header, row)))

    return rows


def parseAmount(text: str) -> float | None:
    """'138,272' 같은 숫자 문자열을 float로 변환."""
    if not text:
        return None
    cleaned = text.replace(",", "").replace(" ", "").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parsePercent(text: str) -> float | None:
    """'18.5%' 같은 비율을 float(0~100)로 변환."""
    if not text:
        return None
    cleaned = text.replace("%", "").replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


# ── 회사명 추출 ──

# 매입처 셀에서 회사명 분리 (쉼표, 및, 등)
_SPLIT_RE = re.compile(r"[,、]|\s+(?:및|and)\s+")
# 뒤에 붙는 " 등", "등", "(...)" 제거
_CLEAN_RE = re.compile(r"(\s*등\s*$|\s*\([^)]*\)\s*$)")


def extractCorpNames(cell: str) -> list[str]:
    """'Qualcomm, MediaTek' 또는 '솔브레인㈜, 동우화인켐㈜ 등' 같은 셀에서 회사명을 분리.

    Returns
    -------
    list[str]
        정제된 회사명 리스트 (㈜/(주) 포함 원본 유지).
    """
    if not cell:
        return []

    # 맨 끝 "등" 제거
    cleaned = _CLEAN_RE.sub("", cell).strip()

    # 쉼표/및로 분리
    parts = [p.strip() for p in _SPLIT_RE.split(cleaned) if p.strip()]

    # 각 이름에서 끝 "등" 제거
    result: list[str] = []
    for p in parts:
        p = _CLEAN_RE.sub("", p).strip()
        if p and len(p) >= 2:
            result.append(p)

    return result


def normalizeCorpName(name: str) -> str:
    """㈜/(주)/주식회사 제거하여 정규화 (매칭용)."""
    if not name:
        return ""
    n = name.strip()
    for suffix in ["㈜", "(주)", "주식회사"]:
        n = n.replace(suffix, "")
    return n.strip()
