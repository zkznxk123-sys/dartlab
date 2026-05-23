"""우발부채 데이터 추출 파이프라인.

P2 통합: 기존 contingentLiability/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class ContingentLiabilityResult:
    """우발부채·채무보증·소송 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        guaranteeDf: 채무보증 시계열 DataFrame
            year | totalGuaranteeAmount | lineCount
        lawsuitDf: 소송 현황 DataFrame
            year | filingDate | parties | description | amount | amountValue | status
    """

    corpName: str | None = None
    nYears: int = 0
    guaranteeDf: pl.DataFrame | None = None
    lawsuitDf: pl.DataFrame | None = None


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
    """
    if not text or not isinstance(text, str):
        return None
    text = text.strip().replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None
    neg = False
    if text.startswith("(") and text.endswith(")"):
        neg = True
        text = text[1:-1]
    elif text.startswith("-") or text.startswith("△") or text.startswith("▲"):
        neg = True
        text = text.lstrip("-△▲")
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        return -val if neg else val
    except ValueError:
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


def classifyBlock(block: list[str]) -> str:
    """블록 타입 분류.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> classifyBlock(...)

    Returns:
        <TODO: return desc> (str)
    """
    text = " ".join(block[:8])

    if "소제기일" in text or "소송 당사자" in text or "소송당사자" in text:
        return "lawsuit"
    if "사건명" in text and ("원고" in text or "피고" in text or "소송" in text):
        return "lawsuit"
    if "소송" in text and ("원고" in text or "피고" in text):
        return "lawsuit"
    if ("채무보증" in text or "보증금액" in text or "지급보증" in text) and "기초" in text and "기말" in text:
        return "guaranteeDetail"
    if "보증금액" in text or "채무보증" in text or "지급보증" in text or "보증내역" in text:
        return "guaranteeSummary"
    if "담보" in text and ("자산" in text or "금액" in text or "제공" in text):
        return "collateral"
    if "약정" in text and ("한도" in text or "실행" in text):
        return "commitment"
    if ("당기말" in text or "당 기 말" in text) and ("전기말" in text or "전 기 말" in text):
        if "보증" in text or "채무" in text:
            return "guaranteeSummary"

    return "other"


def parseGuaranteeSummary(block: list[str]) -> dict | None:
    """채무보증 요약 테이블에서 총 보증금액 추출.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> parseGuaranteeSummary(...)

    Returns:
        <TODO: return desc> (dict | None)
    """
    dataRows = [line for line in block if not isSeparatorRow(line)]

    totalAmount = 0
    count = 0

    for row in dataRows:
        cells = splitCells(row)
        if any("단위" in c for c in cells):
            continue

        for cell in cells:
            c = cell.strip()
            if re.match(r"^[\d,]+$", c):
                val = parseAmount(c)
                if val and val > 0:
                    totalAmount += val
                    count += 1

    if count == 0:
        return None

    return {"totalGuaranteeAmount": totalAmount, "lineCount": count}


def parseGuaranteeDetail(block: list[str]) -> dict | None:
    """채무보증 상세 테이블에서 기말 보증금액 합계 추출.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> parseGuaranteeDetail(...)

    Returns:
        <TODO: return desc> (dict | None)
    """
    dataRows = [line for line in block if not isSeparatorRow(line)]

    endColIdx = None
    for row in dataRows:
        cells = splitCells(row)
        for i, cell in enumerate(cells):
            if "기말" in cell:
                endColIdx = i
                break
        if endColIdx is not None:
            break

    if endColIdx is None:
        return None

    total = 0
    count = 0
    foundHeader = False

    for row in dataRows:
        cells = splitCells(row)
        if "기말" in " ".join(cells):
            foundHeader = True
            continue
        if not foundHeader:
            continue
        if len(cells) <= endColIdx:
            continue

        val = parseAmount(cells[endColIdx])
        if val and val > 0:
            total += val
            count += 1

    if count == 0:
        return None

    return {"totalGuaranteeAmount": total, "lineCount": count}


def parseLawsuit(block: list[str]) -> dict | None:
    """소송 정보 추출 (key-value 형태).

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> parseLawsuit(...)

    Returns:
        <TODO: return desc> (dict | None)
    """
    result: dict = {}

    for line in block:
        if isSeparatorRow(line):
            continue
        cells = splitCells(line)
        if len(cells) < 2:
            continue

        key = cells[0].strip()
        value = cells[1].strip()

        if "소제기일" in key:
            result["filingDate"] = value
        elif "당사자" in key:
            result["parties"] = value
        elif "내용" in key and "소송" in key:
            result["description"] = value
        elif "사건명" in key:
            result["description"] = value
        elif "가액" in key or "금액" in key:
            result["amount"] = value
            m = re.search(r"([\d,]+)", value)
            if m:
                result["amountValue"] = parseAmount(m.group(1))
        elif "진행" in key:
            result["status"] = value

    if not result:
        return None

    return result


# pipeline
def contingentLiability(stockCode: str) -> ContingentLiabilityResult | None:
    """사업보고서에서 우발부채·채무보증·소송 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        ContingentLiabilityResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> contingentLiability(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    guaranteeRows: list[dict] = []
    lawsuitRows: list[dict] = []

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        content = _findSection(report)
        if content is None:
            continue

        blocks = extractTableBlocks(content)
        yearGuarantee = None
        yearLawsuits: list[dict] = []

        for block in blocks:
            kind = classifyBlock(block)

            if kind == "guaranteeDetail" and yearGuarantee is None:
                parsed = parseGuaranteeDetail(block)
                if parsed:
                    yearGuarantee = parsed
                    yearGuarantee["year"] = int(year)

            elif kind == "guaranteeSummary" and yearGuarantee is None:
                parsed = parseGuaranteeSummary(block)
                if parsed:
                    yearGuarantee = parsed
                    yearGuarantee["year"] = int(year)

            elif kind == "lawsuit":
                parsed = parseLawsuit(block)
                if parsed:
                    parsed["year"] = int(year)
                    yearLawsuits.append(parsed)

        if yearGuarantee:
            guaranteeRows.append(yearGuarantee)
        lawsuitRows.extend(yearLawsuits)

    if not guaranteeRows and not lawsuitRows:
        return None

    guaranteeDf = _buildGuaranteeDf(guaranteeRows) if guaranteeRows else None
    lawsuitDf = _buildLawsuitDf(lawsuitRows) if lawsuitRows else None

    return ContingentLiabilityResult(
        corpName=corpName,
        nYears=max(len(guaranteeRows), len({r["year"] for r in lawsuitRows})) if lawsuitRows else len(guaranteeRows),
        guaranteeDf=guaranteeDf,
        lawsuitDf=lawsuitDf,
    )


def _findSection(report: pl.DataFrame) -> str | None:
    """우발부채 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if re.search(r"우발부채", title):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content
    return None


def _buildGuaranteeDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "totalGuaranteeAmount": pl.Int64,
        "lineCount": pl.Int64,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)


def _buildLawsuitDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "filingDate": pl.Utf8,
        "parties": pl.Utf8,
        "description": pl.Utf8,
        "amount": pl.Utf8,
        "amountValue": pl.Int64,
        "status": pl.Utf8,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)
