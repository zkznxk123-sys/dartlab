"""정관에 관한 사항 파이프라인.

P2 통합: 기존 articlesOfIncorporation/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class ArticlesResult:
    """정관에 관한 사항 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    changes: list[dict] = field(default_factory=list)
    purposes: list[dict] = field(default_factory=list)
    noData: bool = False
    changesDf: pl.DataFrame | None = None
    purposesDf: pl.DataFrame | None = None


# parser
def splitCells(line: str) -> list[str]:
    """파이프 구분자로 셀 분리.

    Args:
        line: 인자.

    Raises:
        없음.

    Example:
        >>> splitCells(...)

    Returns:
        <TODO: return desc> (list[str])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    cells = [c.strip() for c in line.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def isSeparatorRow(line: str) -> bool:
    """구분선 행 여부 확인.

    Args:
        line: 인자.

    Raises:
        없음.

    Example:
        >>> isSeparatorRow(...)

    Returns:
        <TODO: return desc> (bool)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    cells = splitCells(line)
    return all(re.match(r"^-+$", c.strip()) for c in cells if c.strip())


def parseArticlesChanges(content: str) -> list[dict]:
    """정관 변경 이력 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseArticlesChanges(...)

    Returns:
        <TODO: return desc> (list[dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    lines = content.split("\n")
    results: list[dict] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                # 사업목적 테이블 시작시 중단
                pass
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        # 헤더 감지
        if any("변경일" in c or "정관변경" in c for c in cells) and any(
            "주총" in c or "변경사항" in c or "변경이유" in c for c in cells
        ):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 사업목적 테이블 시작시 중단
        if any("사업목적" in c for c in cells) and any("영위" in c for c in cells):
            break

        # 데이터 행
        date = cells[0].strip()
        if not date or len(date) < 4:
            continue

        # 날짜가 아닌 행 스킵 (숫자 시작이 아님)
        if not re.search(r"\d{4}", date):
            continue

        entry: dict = {"date": date}
        if len(cells) >= 2:
            entry["meetingName"] = cells[1].strip()
        if len(cells) >= 3:
            entry["changes"] = cells[2].strip()
        if len(cells) >= 4:
            entry["reason"] = cells[3].strip()

        results.append(entry)

    return results


def parseBusinessPurpose(content: str) -> list[dict]:
    """사업목적 현황 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseBusinessPurpose(...)

    Returns:
        <TODO: return desc> (list[dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    lines = content.split("\n")
    results: list[dict] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                # 다른 섹션 시작시 중단 가능
                pass
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        # 헤더 감지
        if any("사업목적" in c for c in cells) and any("영위" in c or "구 분" in c or "구분" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 정관 변경 이력 테이블 만나면 중단 (순서가 바뀐 경우)
        if any("변경일" in c or "정관변경" in c for c in cells):
            break

        # 데이터 행
        purpose = ""
        status = ""

        # 첫 번째 셀이 숫자면 구분 번호
        if len(cells) >= 3:
            purpose = cells[1].strip()
            status = cells[2].strip()
        elif len(cells) == 2:
            purpose = cells[0].strip()
            status = cells[1].strip()

        if not purpose or len(purpose) < 2:
            continue

        # "※" 주석행 스킵
        if purpose.startswith("※") or purpose.startswith("*"):
            continue

        entry: dict = {"purpose": purpose}
        if status:
            entry["active"] = "영위" in status
        results.append(entry)

    return results


# pipeline
def articlesOfIncorporation(stockCode: str) -> ArticlesResult | None:
    """정관에 관한 사항 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> articlesOfIncorporation(...)

    Returns:
        <TODO: return desc> (ArticlesResult | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    try:
        df = loadData(stockCode)
    except FileNotFoundError:
        return None

    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    for year in years[:2]:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if "정관" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                changes = parseArticlesChanges(content)
                purposes = parseBusinessPurpose(content)

                if not changes and not purposes:
                    if "없습니다" in content[:500] or "해당사항" in content[:500]:
                        return ArticlesResult(corpName=corpName, nYears=1, noData=True)
                    continue

                changesDf = None
                if changes:
                    changesDf = pl.DataFrame(changes)

                purposesDf = None
                if purposes:
                    purposesDf = pl.DataFrame(purposes)

                return ArticlesResult(
                    corpName=corpName,
                    nYears=1,
                    changes=changes,
                    purposes=purposes,
                    changesDf=changesDf,
                    purposesDf=purposesDf,
                )
    return None
