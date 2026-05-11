"""직원 현황 데이터 추출 파이프라인.

P2 통합: 기존 employee/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import extractReportYear, selectReport
from dartlab.core.tableParser import parseAmount

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class EmployeeResult:
    """직원 현황 분석 결과."""

    corpName: str | None
    nYears: int
    timeSeries: pl.DataFrame | None = None


# parser
def parseTenure(text: str) -> float | None:
    """평균근속연수 문자열 -> float (년 단위).

    지원 포맷: "13.0", "3년9개월", "12년 10개월", "6개월", "20"
    """
    if not text or text.strip() in ("", "-"):
        return None
    s = text.strip()
    m = re.match(r"(\d+)\s*년\s*(\d+)\s*개월", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 12
    m = re.match(r"(\d+)\s*년", s)
    if m:
        return float(m.group(1))
    m = re.match(r"(\d+)\s*개월", s)
    if m:
        return int(m.group(1)) / 12
    val = parseAmount(s)
    if val is not None and 0 < val < 100:
        return val
    return None


def _tryExtract(cells: list[str], empIdx: int, tenureIdx: int, salaryIdx: int, avgIdx: int) -> dict | None:
    """지정 인덱스로 합계 행에서 직원 데이터 추출."""
    if empIdx >= len(cells):
        return None
    emp = parseAmount(cells[empIdx])
    if emp is None or emp < 1:
        return None
    result: dict = {"totalEmployees": emp}
    if tenureIdx < len(cells):
        tenure = parseTenure(cells[tenureIdx])
        if tenure is not None:
            result["avgTenure"] = round(tenure, 1)
    if salaryIdx < len(cells):
        salary = parseAmount(cells[salaryIdx])
        if salary is not None and salary >= emp:
            result["totalSalary"] = salary
    if avgIdx < len(cells):
        avg = parseAmount(cells[avgIdx])
        if avg is not None:
            result["avgSalary"] = avg
    return result


def parseEmployeeTable(content: str) -> dict:
    """직원 현황 섹션에서 합계 행 파싱.

    Returns:
        dict with keys: totalEmployees, avgTenure, totalSalary, avgSalary.
        파싱 실패 시 빈 dict.
    """
    lines = content.split("\n")

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue

        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if cells[0] not in ("합 계", "합계"):
            continue
        if len(cells) < 4:
            continue

        # 표준 구조: cells[6]=emp, [7]=tenure, [8]=salary, [9]=avg
        if len(cells) >= 10:
            r = _tryExtract(cells, 6, 7, 8, 9)
            if r and r.get("totalSalary"):
                return r

        # shifted 구조: cells[5]=emp, [6]=tenure, [7]=salary, [8]=avg
        if len(cells) >= 9:
            r = _tryExtract(cells, 5, 6, 7, 8)
            if r and r.get("totalSalary"):
                return r

        # 변형 구조: cells[2]=emp, [7]=tenure, [8]=salary, [9]=avg
        if len(cells) >= 10:
            r = _tryExtract(cells, 2, 7, 8, 9)
            if r and r.get("totalSalary"):
                return r

        # salary 없어도 emp만 추출 (한화비전, 스팩)
        if len(cells) >= 10:
            r = _tryExtract(cells, 6, 7, 8, 9)
            if r:
                return r

        # cells[2]에 emp (스팩 일부)
        if len(cells) >= 3:
            maxIdx = len(cells)
            r = _tryExtract(
                cells,
                2,
                7 if maxIdx > 7 else maxIdx,
                8 if maxIdx > 8 else maxIdx,
                9 if maxIdx > 9 else maxIdx,
            )
            if r:
                return r

    return {}


# pipeline
def employee(stockCode: str) -> EmployeeResult | None:
    """사업보고서에서 직원 현황 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        EmployeeResult 또는 데이터 부족 시 None
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    years = sorted(df["year"].unique().to_list(), reverse=True)

    yearData: dict[int, dict] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        empRows = report.filter(
            pl.col("section_title").str.contains("직원") | pl.col("section_title").str.contains("임원")
        )
        if empRows.height == 0:
            continue

        reportYear = extractReportYear(empRows["report_type"][0])
        if reportYear is None:
            continue

        content = empRows["section_content"][0]
        parsed = parseEmployeeTable(content)

        if not parsed.get("totalEmployees"):
            continue

        # avgSalary 있어야 신뢰할 수 있는 데이터
        if not parsed.get("avgSalary"):
            continue

        if reportYear not in yearData:
            yearData[reportYear] = parsed

    if not yearData:
        return None

    records = []
    for yr in sorted(yearData.keys()):
        d = yearData[yr]
        records.append(
            {
                "year": yr,
                "totalEmployees": d.get("totalEmployees"),
                "avgTenure": d.get("avgTenure"),
                "totalSalary": d.get("totalSalary"),
                "avgSalary": d.get("avgSalary"),
            }
        )

    ts = pl.DataFrame(records)

    return EmployeeResult(
        corpName=corpName,
        nYears=ts.height,
        timeSeries=ts,
    )
