"""채무증권 발행실적 데이터 추출 파이프라인.

P2 통합: 기존 bond/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import extractReportYear, selectReport
from dartlab.core.tableParser import parseAmount

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class BondIssuance:
    """개별 채무증권 발행 항목."""

    issuer: str
    bondType: str | None = None
    method: str | None = None
    issueDate: str | None = None
    amount: float | None = None
    interestRate: str | None = None
    rating: str | None = None
    maturityDate: str | None = None
    redeemed: str | None = None
    underwriter: str | None = None


@dataclass
class BondResult:
    """채무증권 발행실적 분석 결과."""

    corpName: str | None
    nYears: int
    issuances: list[BondIssuance] = field(default_factory=list)
    timeSeries: pl.DataFrame | None = None


# parser
def parseBondTable(content: str) -> list[dict]:
    """채무증권 발행실적 10셀 테이블 파싱.

    Returns:
        list[dict] - 각 dict는 BondIssuance 필드와 동일:
            issuer, bondType, method, issueDate, amount,
            interestRate, rating, maturityDate, redeemed, underwriter

    Raises:
        없음.

    Example:
        >>> parseBondTable(...)

    Args:
        content: <TODO: param desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
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

        if len(cells) < 8:
            continue

        txt = " ".join(cells)
        if all(c.replace("-", "") == "" for c in cells):
            continue

        if "발행회사" in txt and "증권종류" in txt:
            inTable = True
            continue

        if not inTable:
            continue

        name = cells[0]
        if name in ("합 계", "합계", "계"):
            break

        if len(cells) < 10:
            continue

        if not name:
            continue

        record = {
            "issuer": name,
            "bondType": cells[1],
            "method": cells[2],
            "issueDate": cells[3],
            "amount": parseAmount(cells[4]),
            "interestRate": cells[5],
            "rating": cells[6],
            "maturityDate": cells[7],
            "redeemed": cells[8],
            "underwriter": cells[9] if len(cells) > 9 else None,
        }
        results.append(record)

    return results


# pipeline
def bond(stockCode: str) -> BondResult | None:
    """사업보고서에서 채무증권 발행실적 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        BondResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> bond(...)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    years = sorted(df["year"].unique().to_list(), reverse=True)

    yearData: dict[int, list[dict]] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        bondRows = report.filter(pl.col("section_title").str.contains("증권의 발행"))
        if bondRows.height == 0:
            continue

        reportYear = extractReportYear(bondRows["report_type"][0])
        if reportYear is None:
            continue

        content = bondRows["section_content"][0]
        parsed = parseBondTable(content)

        if parsed and reportYear not in yearData:
            yearData[reportYear] = parsed

    if not yearData:
        return None

    latestYear = max(yearData.keys())
    latestData = yearData[latestYear]

    issuances = [
        BondIssuance(
            issuer=d["issuer"],
            bondType=d.get("bondType"),
            method=d.get("method"),
            issueDate=d.get("issueDate"),
            amount=d.get("amount"),
            interestRate=d.get("interestRate"),
            rating=d.get("rating"),
            maturityDate=d.get("maturityDate"),
            redeemed=d.get("redeemed"),
            underwriter=d.get("underwriter"),
        )
        for d in latestData
    ]

    records = []
    for yr in sorted(yearData.keys()):
        data = yearData[yr]
        totalAmount = sum(d.get("amount") or 0 for d in data)
        unredeemed = sum(1 for d in data if "미상환" in (d.get("redeemed") or ""))
        records.append(
            {
                "year": yr,
                "totalIssuances": len(data),
                "totalAmount": totalAmount,
                "unredeemedCount": unredeemed,
            }
        )

    ts = pl.DataFrame(records)

    return BondResult(
        corpName=corpName,
        nYears=ts.height,
        issuances=issuances,
        timeSeries=ts,
    )
