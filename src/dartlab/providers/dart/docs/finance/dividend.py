"""배당 데이터 추출 파이프라인.

P2 통합: 기존 dividend/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

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
class DividendResult:
    """배당 분석 결과."""

    corpName: str | None
    nYears: int
    timeSeries: pl.DataFrame | None = None


# parser
def parseDividendTable(content: str) -> dict:
    """배당 섹션 텍스트에서 주요 배당지표 파싱.

    Returns:
        dict with keys: netIncome, eps, totalDividend, payoutRatio,
        dividendYieldCommon, dpsCommon, dpsPreferred.
        각 값은 [당기, 전기, 전전기] 3개 float|None 리스트.

    Raises:
        없음.

    Example:
        >>> parseDividendTable(...)
    """
    lines = content.split("\n")
    tableRows: list[list[str]] = []
    inMainTable = False

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]
        if not cells:
            continue
        if all(c.replace("-", "") == "" for c in cells):
            continue

        cellText = " ".join(cells)
        if "배당지표" in cellText or "단위" in cellText:
            inMainTable = True
            continue
        if "배당 이력" in cellText or "배당이력" in cellText:
            break
        if not inMainTable and "구" in cellText and "분" in cellText and "당기" in cellText:
            inMainTable = True
        if inMainTable or any(
            kw in cellText for kw in ["주당액면가액", "당기순이익", "현금배당금", "배당성향", "배당수익률"]
        ):
            inMainTable = True
            tableRows.append(cells)

    result = {
        "netIncome": [],
        "eps": [],
        "totalDividend": [],
        "payoutRatio": [],
        "dividendYieldCommon": [],
        "dpsCommon": [],
        "dpsPreferred": [],
    }

    prevLabel = ""
    for row in tableRows:
        if len(row) < 3:
            continue

        label = row[0].strip()
        if not label:
            label = prevLabel

        stockType = ""
        values = row[1:]
        if len(row) >= 4:
            second = row[1].strip()
            if second in ("보통주", "우선주", "종류주", "1우선주(주1)", "1우선주"):
                stockType = "우선주" if "우선" in second else ("종류주" if "종류" in second else "보통주")
                values = row[2:]
            elif label in ("보통주", "우선주", "종류주", "1우선주(주1)", "1우선주"):
                stockType = "우선주" if "우선" in label else ("종류주" if "종류" in label else "보통주")
                label = prevLabel
                values = row[1:]

        amounts = [parseAmount(v) for v in values[:3]]
        while len(amounts) < 3:
            amounts.append(None)

        if "당기순이익" in label and "연결" in label:
            result["netIncome"] = amounts
        elif "당기순이익" in label and (not result["netIncome"] or all(a is None for a in result["netIncome"])):
            result["netIncome"] = amounts
        elif "주당순이익" in label:
            result["eps"] = amounts
        elif "현금배당금총액" in label:
            result["totalDividend"] = amounts
        elif "현금배당성향" in label:
            result["payoutRatio"] = amounts
        elif "현금배당수익률" in label:
            if stockType == "우선주" or label == "우선주":
                pass
            elif stockType == "종류주" and all(a is None for a in amounts):
                pass
            else:
                result["dividendYieldCommon"] = amounts
        elif "주당" in label and "현금배당금" in label:
            if stockType == "우선주" or label == "우선주":
                result["dpsPreferred"] = amounts
            elif stockType == "종류주" and all(a is None for a in amounts):
                pass
            else:
                result["dpsCommon"] = amounts

        if label and label not in ("보통주", "우선주", "종류주"):
            prevLabel = label

    return result


# pipeline
def dividend(stockCode: str) -> DividendResult | None:
    """사업보고서에서 배당지표 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        DividendResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> dividend(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    years = sorted(df["year"].unique().to_list(), reverse=True)

    yearData: dict[int, dict[str, float]] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        divRows = report.filter(pl.col("section_title").str.contains("배당"))
        if divRows.height == 0:
            continue

        content = divRows["section_content"][0]
        reportYear = extractReportYear(divRows["report_type"][0])
        if reportYear is None:
            continue

        parsed = parseDividendTable(content)
        offsets = [0, -1, -2]

        for field in [
            "netIncome",
            "eps",
            "totalDividend",
            "payoutRatio",
            "dividendYieldCommon",
            "dpsCommon",
            "dpsPreferred",
        ]:
            vals = parsed.get(field, [])
            for j, offset in enumerate(offsets):
                if j < len(vals) and vals[j] is not None:
                    yr = reportYear + offset
                    if yr not in yearData:
                        yearData[yr] = {}
                    if field not in yearData[yr]:
                        yearData[yr][field] = vals[j]

    if not yearData:
        return None

    records = []
    for yr in sorted(yearData.keys()):
        d = yearData[yr]
        records.append(
            {
                "year": yr,
                "netIncome": d.get("netIncome"),
                "eps": d.get("eps"),
                "totalDividend": d.get("totalDividend"),
                "payoutRatio": d.get("payoutRatio"),
                "dividendYield": d.get("dividendYieldCommon"),
                "dps": d.get("dpsCommon"),
                "dpsPreferred": d.get("dpsPreferred"),
            }
        )

    ts = pl.DataFrame(records)

    return DividendResult(
        corpName=corpName,
        nYears=ts.height,
        timeSeries=ts,
    )
