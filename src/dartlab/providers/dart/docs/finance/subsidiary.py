"""타법인출자 현황 데이터 추출 파이프라인.

P2 통합: 기존 subsidiary/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers._common.reportSelector import extractReportYear, selectReport
from dartlab.providers._common.tableParser import parseAmount

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class SubsidiaryInvestment:
    """개별 타법인 출자 항목."""

    name: str
    listed: str | None = None
    firstAcquired: str | None = None
    purpose: str | None = None
    firstAmount: float | None = None
    beginShares: float | None = None
    beginRatio: float | None = None
    beginBook: float | None = None
    acquiredShares: float | None = None
    acquiredAmount: float | None = None
    valuationGain: float | None = None
    endShares: float | None = None
    endRatio: float | None = None
    endBook: float | None = None
    totalAssets: float | None = None
    netIncome: float | None = None


@dataclass
class SubsidiaryResult:
    """타법인출자 현황 분석 결과."""

    corpName: str | None
    nYears: int
    investments: list[SubsidiaryInvestment] = field(default_factory=list)
    timeSeries: pl.DataFrame | None = None


# parser
def parseSubsidiaryTable(content: str) -> list[dict]:
    """타법인출자 현황 16셀 테이블 파싱.

    Returns:
        list[dict] - 각 dict는 SubsidiaryInvestment 필드와 동일:
            name, listed, firstAcquired, purpose, firstAmount,
            beginShares, beginRatio, beginBook,
            acquiredShares, acquiredAmount, valuationGain,
            endShares, endRatio, endBook,
            totalAssets, netIncome

    Raises:
        없음.

    Example:
        >>> parseSubsidiaryTable(...)

    Args:
        content: str.
    """
    lines = content.split("\n")
    results = []
    inTable = False

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue

        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if len(cells) < 10:
            continue

        txt = " ".join(cells)
        if all(c.replace("-", "") == "" for c in cells):
            continue

        if "법인명" in txt or "법 인 명" in txt:
            inTable = True
            continue

        if not inTable:
            continue

        if "수량" in cells[0] and ("지분율" in txt or "금액" in txt):
            continue

        name = cells[0]
        if name in ("합 계", "합계", "계"):
            break

        if len(cells) < 16:
            continue

        if not name or name in ("수량", "지분율", "장부가액"):
            continue

        record = {
            "name": name,
            "listed": cells[1],
            "firstAcquired": cells[2],
            "purpose": cells[3],
            "firstAmount": parseAmount(cells[4]),
            "beginShares": parseAmount(cells[5]),
            "beginRatio": parseAmount(cells[6]),
            "beginBook": parseAmount(cells[7]),
            "acquiredShares": parseAmount(cells[8]),
            "acquiredAmount": parseAmount(cells[9]),
            "valuationGain": parseAmount(cells[10]),
            "endShares": parseAmount(cells[11]),
            "endRatio": parseAmount(cells[12]),
            "endBook": parseAmount(cells[13]),
            "totalAssets": parseAmount(cells[14]),
            "netIncome": parseAmount(cells[15]),
        }
        results.append(record)

    return results


# pipeline
def subsidiary(stockCode: str) -> SubsidiaryResult | None:
    """사업보고서에서 타법인출자 현황 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        SubsidiaryResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> subsidiary(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    years = sorted(df["year"].unique().to_list(), reverse=True)

    yearData: dict[int, list[dict]] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        subRows = report.filter(pl.col("section_title").str.contains("타법인"))
        if subRows.height == 0:
            subRows = report.filter(pl.col("section_title").str.contains("출자"))
        if subRows.height == 0:
            continue

        reportYear = extractReportYear(subRows["report_type"][0])
        if reportYear is None:
            continue

        for ri in range(subRows.height):
            content = subRows["section_content"][ri]
            parsed = parseSubsidiaryTable(content)
            if parsed:
                if reportYear not in yearData:
                    yearData[reportYear] = parsed
                break

    if not yearData:
        return None

    latestYear = max(yearData.keys())
    latestData = yearData[latestYear]

    investments = [
        SubsidiaryInvestment(
            name=d["name"],
            listed=d.get("listed"),
            firstAcquired=d.get("firstAcquired"),
            purpose=d.get("purpose"),
            firstAmount=d.get("firstAmount"),
            beginShares=d.get("beginShares"),
            beginRatio=d.get("beginRatio"),
            beginBook=d.get("beginBook"),
            acquiredShares=d.get("acquiredShares"),
            acquiredAmount=d.get("acquiredAmount"),
            valuationGain=d.get("valuationGain"),
            endShares=d.get("endShares"),
            endRatio=d.get("endRatio"),
            endBook=d.get("endBook"),
            totalAssets=d.get("totalAssets"),
            netIncome=d.get("netIncome"),
        )
        for d in latestData
    ]

    records = []
    for yr in sorted(yearData.keys()):
        data = yearData[yr]
        totalBook = sum(d.get("endBook") or 0 for d in data)
        listedCount = sum(1 for d in data if d.get("listed") == "상장")
        unlistedCount = len(data) - listedCount
        records.append(
            {
                "year": yr,
                "totalCount": len(data),
                "listedCount": listedCount,
                "unlistedCount": unlistedCount,
                "totalBook": totalBook,
            }
        )

    ts = pl.DataFrame(records)

    return SubsidiaryResult(
        corpName=corpName,
        nYears=ts.height,
        investments=investments,
        timeSeries=ts,
    )
