"""제재 현황 데이터 추출 파이프라인.

P2 통합: 기존 sanction/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class SanctionResult:
    """제재 현황 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        sanctionDf: 제재 현황 DataFrame
            year | date | agency | subject | action | amount | reason
    """

    corpName: str | None = None
    nYears: int = 0
    sanctionDf: pl.DataFrame | None = None


# parser
def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseAmount(...)

    Returns:
        <TODO: return desc> (int | None)

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
    if not text or not isinstance(text, str):
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        if abs(val) > 9_000_000_000_000_000_000:
            return None
        return val
    except (ValueError, OverflowError):
        return None


def extractTableBlocks(content: str) -> list[list[str]]:
    """content에서 |(pipe) 구분 테이블 블록들 추출.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> extractTableBlocks(...)

    Returns:
        <TODO: return desc> (list[list[str]])

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
    """splitCells — TODO 한국어 동작 설명.

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
    cells = [c.strip() for c in line.split("|")]
    while cells and cells[0] == "":
        cells.pop(0)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def isSeparatorRow(line: str) -> bool:
    """isSeparatorRow — TODO 한국어 동작 설명.

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
    cells = splitCells(line)
    return all(re.match(r"^-+$", c.strip()) for c in cells if c.strip())


def parseSanctionTable(block: list[str]) -> list[dict]:
    """제재 테이블 파싱.

    구조:
    | 일자 | 제재기관 | 대상자 | 처벌/조치 내용 | 금전적 제재금액 | 사유 및 근거 법령 |

    Returns:
        [{date, agency, subject, action, amount, reason}, ...]

    Raises:
        없음.

    Example:
        >>> parseSanctionTable(...)

    Args:
        block: <TODO: param desc> (list[str])

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
    dataRows = [line for line in block if not isSeparatorRow(line)]
    if len(dataRows) < 3:
        return []

    # 헤더 컬럼 인덱스 찾기
    dateIdx = agencyIdx = subjectIdx = actionIdx = amountIdx = reasonIdx = None
    headerRow = None

    for row in dataRows:
        cells = splitCells(row)
        for i, cell in enumerate(cells):
            c = cell.strip()
            if "일자" in c and dateIdx is None:
                dateIdx = i
            if ("제재기관" in c or "처분기관" in c) and agencyIdx is None:
                agencyIdx = i
            if "대상" in c and subjectIdx is None:
                subjectIdx = i
            if ("처벌" in c or "조치" in c) and "내용" in c and actionIdx is None:
                actionIdx = i
            if ("금액" in c or "금전" in c) and amountIdx is None:
                amountIdx = i
            if ("사유" in c or "근거" in c) and reasonIdx is None:
                reasonIdx = i

        if dateIdx is not None:
            headerRow = row
            break

    if dateIdx is None:
        return []

    results = []
    foundHeader = False
    for row in dataRows:
        if row == headerRow:
            foundHeader = True
            continue
        if not foundHeader:
            continue

        cells = splitCells(row)
        if len(cells) < 3:
            continue
        # 단위 행 건너뛰기
        if any("단위" in c for c in cells):
            continue

        entry: dict = {}
        if dateIdx is not None and dateIdx < len(cells):
            entry["date"] = cells[dateIdx].strip()
        if agencyIdx is not None and agencyIdx < len(cells):
            entry["agency"] = cells[agencyIdx].strip()
        if subjectIdx is not None and subjectIdx < len(cells):
            entry["subject"] = cells[subjectIdx].strip()
        if actionIdx is not None and actionIdx < len(cells):
            entry["action"] = cells[actionIdx].strip()
        if amountIdx is not None and amountIdx < len(cells):
            entry["amount"] = cells[amountIdx].strip()
            entry["amountValue"] = parseAmount(cells[amountIdx])
        if reasonIdx is not None and reasonIdx < len(cells):
            entry["reason"] = cells[reasonIdx].strip()

        if entry.get("date") or entry.get("agency") or entry.get("action"):
            results.append(entry)

    return results


# pipeline
def sanction(stockCode: str) -> SanctionResult | None:
    """사업보고서에서 제재 현황 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        SanctionResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> sanction(...)

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
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    allRows: list[dict] = []

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        content = _findSection(report)
        if content is None:
            continue

        blocks = extractTableBlocks(content)
        for block in blocks:
            entries = parseSanctionTable(block)
            for entry in entries:
                entry["year"] = int(year)
                allRows.append(entry)

    if not allRows:
        return None

    sanctionDf = _buildSanctionDf(allRows)

    return SanctionResult(
        corpName=corpName,
        nYears=len({r["year"] for r in allRows}),
        sanctionDf=sanctionDf,
    )


def _findSection(report: pl.DataFrame) -> str | None:
    """제재 현황 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if re.search(r"제재", title):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content
    return None


def _buildSanctionDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "date": pl.Utf8,
        "agency": pl.Utf8,
        "subject": pl.Utf8,
        "action": pl.Utf8,
        "amount": pl.Utf8,
        "amountValue": pl.Int64,
        "reason": pl.Utf8,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)
