"""배당 데이터 추출 파이프라인.

P2 통합: 기존 dividend/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.frame.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import extractReportYear, selectReport
from dartlab.providers.tableParser import parseAmount

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

    Args:
        content: <TODO: param desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars

    Capabilities:
        - <TODO: 함수 핵심 책임 요약>

    Guide:
        - <TODO: 사용 시나리오>

    AIContext:
        <TODO: AI 호출 컨텍스트>

    LLM Specifications:
        AntiPatterns:
            - <TODO: 안티패턴>
        OutputSchema:
            - <TODO: 출력 형태>
        Prerequisites:
            - <TODO: 사전조건>
        Freshness:
            - <TODO: 데이터 freshness>
        Dataflow:
            - <TODO: 데이터 흐름>
        TargetMarkets:
            - <TODO: 대상 시장>
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
    """사업보고서 (annual) 의 배당 섹션에서 7 지표 시계열 ``DividendResult`` 빌드.

    Capabilities:
        - ``loadData(stockCode)`` 로 전체 정기보고서 parquet 로드 → 연도별 사업보고서 selectReport.
        - ``section_title`` contains "배당" 필터로 배당 섹션 row 추출.
        - ``parseDividendTable`` 로 7 지표 [당기/전기/전전기] 3 값 묶음 파싱.
        - 보고서 연도 - {0, -1, -2} offset → 실제 연도 매핑 (사업보고서 1 개에서 3 년치 데이터 추출).
        - 동일 (year, field) 중복 등장 시 첫 값 보존 (최신 보고서 우선).
        - 결과 = year (int) × {netIncome, eps, totalDividend, payoutRatio, dividendYield,
          dps, dpsPreferred} long-format DataFrame.

    Args:
        stockCode: KR 종목코드 6 자리 (예 "005930").

    Returns:
        ``DividendResult`` — corpName / nYears / timeSeries (pl.DataFrame). 배당 섹션 미존재
        또는 파싱 실패 → None.

    Example:
        >>> from dartlab.providers.dart.docs.finance.dividend import dividend
        >>> r = dividend("005930")
        >>> r is None or r.nYears >= 0
        True

    Guide:
        - "삼성전자 배당 추세" → ``dividend("005930").timeSeries.select(["year", "dps", "dividendYield"])``.
        - "5 년 배당성향 변화" → ``timeSeries.select(["year", "payoutRatio"])``.
        - "보통주 vs 우선주 DPS" → ``["dps", "dpsPreferred"]``.
        - 정기보고서 batch 미수집 회사 → None — caller fallback "배당 데이터 미수집".

    SeeAlso:
        - ``parseDividendTable`` — 본 함수의 파싱 단계 (배당 섹션 → 7 지표 dict).
        - ``DividendResult`` (dataclass) — 본 함수 반환 타입.
        - ``dartlab.providers.dart.docs.finance.statements.statements`` — 같은 패턴 (재무제표 시계열).
        - ``dartlab.providers.dart.report.pivot.pivotDividend`` — report API (parquet 기반) 동등 함수.
        - ``dartlab.providers.reportSelector.selectReport`` — 사업보고서 선택.

    Requires:
        - polars — DataFrame.
        - dartlab.frame.dataLoader — ``loadData`` + ``extractCorpName``.
        - dartlab.providers.reportSelector — ``selectReport`` + ``extractReportYear``.
        - dartlab.providers.tableParser — ``parseAmount`` (parseDividendTable 경유).

    AIContext:
        Workbench "이 회사 배당 어떻게 변했냐"/"DPS 추세" 질문의 entry. ``report.pivotDividend``
        (parquet 기반) 와 본 함수 (text 파싱 기반) 두 경로 — gather 가 어느 쪽을 수집했냐에
        따라 선택. timeSeries 가 long format 이라 AI 가 직접 시각화 (line plot) 또는 비교 분석
        제시 가능.

    LLM Specifications:
        AntiPatterns:
            - 사업보고서 배당 섹션 표 변형 (회사별 column 순서/명칭 차이) → ``parseDividendTable``
              매칭 실패 → 일부 field 누락. timeSeries 의 null 비율로 판정.
            - 우선주만 발행한 회사 → dpsCommon = None, dpsPreferred 만 채워짐.
            - 정기보고서 미제출 또는 배당 섹션 비어있음 → None.
        OutputSchema:
            - 1 DividendResult instance.
            - timeSeries: pl.DataFrame — year (Int) + 7 float columns (각 nullable).
            - nYears: timeSeries.height (year 개수).
        Prerequisites:
            - gather (정기보고서) 가 stockCode 의 사업보고서 1 개 이상 수집.
        Freshness:
            - gather 의존. 본 함수 무상태.
        Dataflow:
            - loadData → selectReport → parseDividendTable → 본 함수 → caller (AI 답변).
        TargetMarkets:
            - KR (DART) 한정. EDGAR 의 dividend 는 별도 (Form 4 / 8-K 또는 XBRL).

    Raises:
        없음.
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
