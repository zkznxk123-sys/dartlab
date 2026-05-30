"""내부통제 데이터 추출 파이프라인.

P2 통합: 기존 internalControl/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers._common.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class InternalControlResult:
    """내부통제 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        controlDf: 내부회계관리제도 시계열 DataFrame
            year | opinion | auditor | hasWeakness
    """

    corpName: str | None = None
    nYears: int = 0
    controlDf: pl.DataFrame | None = None


# parser
def extractTableBlocks(content: str) -> list[list[str]]:
    """content에서 |(pipe) 구분 테이블 블록들 추출.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> extractTableBlocks(...)

    Returns:
        list[list[str]] — 결과.
    """
    lines = content.split("\n")
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        stripped = line.strip()
        if "|" in stripped:
            current.append(stripped)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    return blocks


def splitCells(line: str) -> list[str]:
    """markdown table 한 행을 cell 리스트로 분할 — 앞뒤 빈 cell 제거.

    Args:
        line: ``"| 셀1 | 셀2 |"`` 형식의 markdown 표 행.

    Returns:
        앞뒤 빈 cell 제거된 cell 문자열 list.

    Raises:
        없음.

    Example:
        >>> splitCells("| a | b |")
        ['a', 'b']
    """
    cells = [c.strip() for c in line.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def isSeparatorRow(line: str) -> bool:
    """markdown table separator row (``|---|---|`` 같은 ``-`` 만의 cell) 여부.

    Args:
        line: 표 행 문자열.

    Returns:
        모든 cell 이 ``-`` 만 으로 구성되면 True.

    Raises:
        없음.

    Example:
        >>> isSeparatorRow("|---|---|")
        True
    """
    cells = splitCells(line)
    return all(re.match(r"^-+$", c.strip()) for c in cells if c.strip())


def parseInternalControlTable(block: list[str]) -> list[dict]:
    """내부회계관리제도 테이블 파싱.

    구조:
    | 사업연도 | 구분 | 운영실태 보고일 | 평가 결론 | 중요한취약점 | 시정조치 |
    | 제56기 | 내부회계관리제도 | 2025.01.24 | 효과적... | 해당사항없음 | ... |

    또는 감사인 검토 테이블:
    | 사업연도 | 감사인 | 검토(감사)의견 | 지적사항 |

    Returns:
        [{period, opinion, auditor, hasWeakness}, ...]

    Raises:
        없음.

    Example:
        >>> parseInternalControlTable(...)

    Args:
        block: list[str].
    """
    dataRows = [line for line in block if not isSeparatorRow(line)]
    if len(dataRows) < 3:
        return []

    blockText = " ".join(dataRows)

    # 감사인 검토 테이블인지 확인
    isAuditReview = "감사인" in blockText and ("검토" in blockText or "감사의견" in blockText)

    # 경영진 평가 테이블인지 확인
    isManagementEval = "평가" in blockText and ("결론" in blockText or "효과" in blockText)

    if not isAuditReview and not isManagementEval:
        return []

    results = []

    for row in dataRows:
        cells = splitCells(row)
        if len(cells) < 3:
            continue
        # 단위행/헤더 건너뛰기
        if any(c.strip() in ("---", "사업연도", "구 분", "구분") for c in cells[:2]):
            continue
        if any("단위" in c for c in cells):
            continue

        " ".join(cells)

        # 기 정보 추출 (제56기, 제55기 등)
        period = None
        for cell in cells:
            m = re.search(r"제?\d+기", cell)
            if m:
                period = m.group()
                break

        if period is None:
            continue

        entry: dict = {"period": period}

        if isAuditReview:
            # 감사인 추출
            for cell in cells:
                c = cell.strip()
                if c and "회계법인" in c or "감사법인" in c:
                    entry["auditor"] = c
                    break
                # 일반 감사인명 (삼일, 삼정, 안진, 한영 등)
                if c and re.match(r"(삼일|삼정|안진|한영|대주|성현|신한|이촌|다산)", c):
                    entry["auditor"] = c
                    break

            # 의견 추출
            for cell in cells:
                c = cell.strip()
                if "적정" in c or "유효" in c or "효과" in c:
                    entry["opinion"] = c
                    break
                if "비적정" in c or "부적정" in c:
                    entry["opinion"] = c
                    break

        elif isManagementEval:
            # 평가 결론 추출
            for cell in cells:
                c = cell.strip()
                if "효과" in c or "적정" in c:
                    entry["opinion"] = c[:100]
                    break

            # 중요한 취약점 여부
            for cell in cells:
                c = cell.strip()
                if "해당사항" in c or "해당없음" in c or "없음" in c:
                    entry["hasWeakness"] = False
                    break
                if "취약점" in c and ("있" in c or "발견" in c):
                    entry["hasWeakness"] = True
                    break

        if entry.get("opinion") or entry.get("auditor"):
            results.append(entry)

    return results


# pipeline
def internalControl(stockCode: str) -> InternalControlResult | None:
    """사업보고서에서 내부회계관리제도 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        InternalControlResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> internalControl(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    allRows: list[dict] = []
    seenPeriods: set[str] = set()

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        content = _findSection(report)
        if content is None:
            continue

        blocks = extractTableBlocks(content)
        for block in blocks:
            entries = parseInternalControlTable(block)
            for entry in entries:
                period = entry.get("period", "")
                if period not in seenPeriods:
                    seenPeriods.add(period)
                    entry["year"] = int(year)
                    allRows.append(entry)

    if not allRows:
        return None

    controlDf = _buildControlDf(allRows)

    return InternalControlResult(
        corpName=corpName,
        nYears=len(allRows),
        controlDf=controlDf,
    )


def _findSection(report: pl.DataFrame) -> str | None:
    """내부통제 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if re.search(r"내부통제|내부회계", title):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content
    return None


def _buildControlDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "period": pl.Utf8,
        "opinion": pl.Utf8,
        "auditor": pl.Utf8,
        "hasWeakness": pl.Boolean,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)
