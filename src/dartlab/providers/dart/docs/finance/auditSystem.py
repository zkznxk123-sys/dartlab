"""감사제도에 관한 사항 파이프라인.

P2 통합: 기존 auditSystem/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers._common.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class AuditSystemResult:
    """감사제도에 관한 사항 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    committee: list[dict] = field(default_factory=list)
    activity: list[dict] = field(default_factory=list)
    textOnly: bool = False
    committeeDf: pl.DataFrame | None = None
    activityDf: pl.DataFrame | None = None


# parser
def splitCells(line: str) -> list[str]:
    """파이프(|)로 구분된 셀을 분리.

    Args:
        line: 인자.

    Raises:
        없음.

    Example:
        >>> splitCells(...)

    Returns:
        list[str] — 결과.
    """
    cells = [c.strip() for c in line.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def isSeparatorRow(line: str) -> bool:
    """구분선 행인지 확인.

    Args:
        line: 인자.

    Raises:
        없음.

    Example:
        >>> isSeparatorRow(...)

    Returns:
        bool — 결과.
    """
    cells = splitCells(line)
    return all(re.match(r"^-+$", c.strip()) for c in cells if c.strip())


def parseAuditCommittee(content: str) -> list[dict]:
    """감사위원회 위원 현황 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseAuditCommittee(...)

    Returns:
        list[dict] — 결과.
    """
    lines = content.split("\n")
    results: list[dict] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        # 헤더 감지
        if any("성명" in c or "위원" in c for c in cells) and any(
            "직위" in c or "구분" in c or "경력" in c or "사외" in c or "재직" in c for c in cells
        ):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 데이터 행
        name = cells[0].strip()
        if not name or len(name) < 2 or name in ("합계", "합 계", "소계"):
            continue

        entry: dict = {"name": name}
        if len(cells) >= 2:
            entry["role"] = cells[1].strip()
        if len(cells) >= 3:
            entry["detail"] = cells[2].strip()

        results.append(entry)

    return results


def parseAuditActivity(content: str) -> list[dict]:
    """감사 활동 내역 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseAuditActivity(...)

    Returns:
        list[dict] — 결과.
    """
    lines = content.split("\n")
    results: list[dict] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        if any("개최일자" in c or "일자" in c for c in cells) and any(
            "의안" in c or "안건" in c or "내용" in c or "보고" in c for c in cells
        ):
            headerFound = True
            continue

        if not headerFound:
            continue

        date = cells[0].strip()
        if not date or not re.search(r"\d{4}", date):
            continue

        agenda = cells[1].strip() if len(cells) >= 2 else ""
        entry: dict = {"date": date}
        if agenda:
            entry["agenda"] = agenda
        if len(cells) >= 3:
            entry["result"] = cells[2].strip()

        results.append(entry)

    return results


# pipeline
def auditSystem(stockCode: str) -> AuditSystemResult | None:
    """감사제도에 관한 사항 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> auditSystem(...)

    Returns:
        AuditSystemResult | None — 결과.
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
            if "감사" in title and ("제도" in title or "기구" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                committee = parseAuditCommittee(content)
                activity = parseAuditActivity(content)

                if committee or activity:
                    committeeDf = pl.DataFrame(committee) if committee else None
                    activityDf = pl.DataFrame(activity) if activity else None

                    return AuditSystemResult(
                        corpName=corpName,
                        nYears=1,
                        committee=committee,
                        activity=activity,
                        committeeDf=committeeDf,
                        activityDf=activityDf,
                    )

                if len(content) > 200:
                    return AuditSystemResult(
                        corpName=corpName,
                        nYears=1,
                        textOnly=True,
                    )
    return None
