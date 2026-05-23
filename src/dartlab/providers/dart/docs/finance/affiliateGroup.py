"""계열회사 현황 파이프라인.

P2 통합: 기존 affiliateGroup/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class AffiliateGroupResult:
    """계열회사 현황 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        groupName: 기업집단명 (예: "삼성", "현대자동차")
        listedCount: 상장 계열사 수
        unlistedCount: 비상장 계열사 수
        totalCount: 총 계열사 수
        affiliates: 계열사 목록 [{name, listed}, ...]
        affiliateDf: 계열사 목록 DataFrame
            name | listed
    """

    corpName: str | None = None
    nYears: int = 0
    groupName: str | None = None
    listedCount: int | None = None
    unlistedCount: int | None = None
    totalCount: int | None = None
    affiliates: list[dict] = field(default_factory=list)
    affiliateDf: pl.DataFrame | None = None


# parser
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


def parseGroupSummary(content: str) -> dict | None:
    """요약 테이블에서 그룹명, 상장수, 비상장수 추출.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseGroupSummary(...)

    Returns:
        dict | None — 결과.
    """
    lines = content.split("\n")

    skipNames = {"상장", "비상장", "계", "상장여부", "기업집단의 명칭", "---"}

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped:
            continue
        cells = splitCells(stripped)

        if len(cells) >= 4:
            name = cells[0].strip()
            nums = []
            for c in cells[1:]:
                c = c.strip().replace(",", "")
                if re.match(r"^\d+$", c):
                    nums.append(int(c))

            if len(nums) >= 3 and not re.match(r"^\d+$", name) and name not in skipNames:
                return {
                    "groupName": name,
                    "listedCount": nums[0],
                    "unlistedCount": nums[1],
                    "totalCount": nums[2],
                }

    return None


def _isCompanyName(text: str) -> bool:
    """텍스트가 기업명인지 판별."""
    if not text or len(text) < 2:
        return False
    if re.match(r"^[\d\-−–]+$", text):
        return False
    if re.match(r"^\d{10,}$", text.replace("-", "")):
        return False
    if text in ("-", "−", "–", "없음", "해당없음"):
        return False
    if text.startswith("※") or "참조" in text or "본문 위치" in text:
        return False
    return True


def parseAffiliateList(content: str) -> list[dict]:
    """상세표에서 국내 계열사 목록 추출.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseAffiliateList(...)

    Returns:
        list[dict] — 결과.
    """
    # 해외 섹션 이전까지만 사용
    cutoff = len(content)
    for marker in ["해외계열회사", "해외 계열회사", "나. 해외", "2) 해외법인", "2) 해외"]:
        idx = content.find(marker)
        if idx > 0:
            cutoff = min(cutoff, idx)

    lines = content[:cutoff].split("\n")
    results: list[dict] = []
    currentStatus = None

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        if any(c in ("상장여부", "기업명", "회사수") for c in cells):
            continue
        if any("본문 위치" in c or "기준일" in c or "단위" in c for c in cells):
            continue

        first = cells[0].strip()

        if first in ("상장", "비상장"):
            currentStatus = first
            for c in cells[1:]:
                c = c.strip()
                if re.match(r"^\d+$", c):
                    continue
                if _isCompanyName(c):
                    results.append({"name": c, "listed": currentStatus == "상장"})
            continue

        if currentStatus is not None:
            if _isCompanyName(first):
                results.append({"name": first, "listed": currentStatus == "상장"})

    return results


# pipeline
def affiliateGroup(stockCode: str) -> AffiliateGroupResult | None:
    """계열회사 현황 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> affiliateGroup(...)

    Returns:
        AffiliateGroupResult | None — 결과.
    """
    try:
        df = loadData(stockCode)
    except FileNotFoundError:
        return None

    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        # 1. 상세표에서 계열사 목록
        affiliates: list[dict] = []
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if "계열회사 현황" in title and "상세" in title:
                content = row.get("section_content", "") or ""
                if len(content) > 30:
                    affiliates = parseAffiliateList(content)
                break

        # 2. 본문에서 요약 (그룹명, 상장/비상장 수)
        summary = None
        for row in report.iter_rows(named=True):
            title = row.get("section_title", "") or ""
            if re.search(r"계열회사.*사항", title):
                content = row.get("section_content", "") or ""
                if len(content) > 30:
                    summary = parseGroupSummary(content)
                break

        if not affiliates and summary is None:
            continue

        listedCompanies = [a for a in affiliates if a["listed"]]
        unlistedCompanies = [a for a in affiliates if not a["listed"]]

        groupName = summary["groupName"] if summary else None
        listedCount = summary["listedCount"] if summary else len(listedCompanies)
        unlistedCount = summary["unlistedCount"] if summary else len(unlistedCompanies)
        totalCount = summary["totalCount"] if summary else len(affiliates)

        affiliateDf = None
        if affiliates:
            affiliateDf = pl.DataFrame(
                {
                    "name": [a["name"] for a in affiliates],
                    "listed": [a["listed"] for a in affiliates],
                },
                schema={"name": pl.Utf8, "listed": pl.Boolean},
            )

        return AffiliateGroupResult(
            corpName=corpName,
            nYears=1,
            groupName=groupName,
            listedCount=listedCount,
            unlistedCount=unlistedCount,
            totalCount=totalCount,
            affiliates=affiliates,
            affiliateDf=affiliateDf,
        )

    return None
