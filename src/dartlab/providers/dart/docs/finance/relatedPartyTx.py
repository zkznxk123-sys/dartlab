"""대주주 거래 데이터 추출 파이프라인.

P2 통합: 기존 relatedPartyTx/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class RelatedPartyTxResult:
    """대주주 등과의 거래내용 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        guaranteeDf: 채무보증 시계열 DataFrame
            year | entity | relationship | amount
        assetTxDf: 자산 거래 시계열 DataFrame
            year | entity | txType | amount
        revenueTxDf: 매출입 거래 시계열 DataFrame
            year | entity | sales | purchases
    """

    corpName: str | None = None
    nYears: int = 0
    guaranteeDf: pl.DataFrame | None = None
    assetTxDf: pl.DataFrame | None = None
    revenueTxDf: pl.DataFrame | None = None


# parser
def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseAmount(...)
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
        # Polars Int64 범위 초과 방지
        if abs(val) > 9_000_000_000_000_000_000:
            return None
        return -val if neg else val
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
    """
    text = " ".join(block[:8])

    if "채무보증" in text or "지급보증" in text or "보증금액" in text:
        return "guarantee"
    if "자산" in text and ("양수" in text or "양도" in text or "매각" in text or "매입" in text):
        return "assetTx"
    if "매출" in text and ("매입" in text or "매출입" in text):
        return "revenueTx"
    if "대여금" in text or "차입금" in text:
        return "loan"
    if "출자" in text or "출자지분" in text:
        return "investment"

    return "other"


def parseGuaranteeBlock(block: list[str]) -> list[dict]:
    """채무보증 블록에서 보증 건별 데이터 추출.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> parseGuaranteeBlock(...)
    """
    dataRows = [line for line in block if not isSeparatorRow(line)]
    results = []

    for row in dataRows:
        cells = splitCells(row)
        if len(cells) < 4:
            continue
        if any("단위" in c for c in cells):
            continue
        # 헤더 행 건너뛰기
        if any(c in ("법인명", "성명", "채무자", "보증내역") for c in cells[:2]):
            continue

        # 첫 번째 셀이 엔티티명
        entity = cells[0].strip()
        if not entity or entity in ("-", ""):
            continue

        # 숫자 셀 추출
        amounts = []
        for cell in cells[1:]:
            val = parseAmount(cell)
            if val is not None:
                amounts.append(val)

        if amounts:
            results.append(
                {
                    "entity": entity,
                    "amount": max(amounts),
                }
            )

    return results


def parseRevenueTxBlock(block: list[str]) -> list[dict]:
    """매출입 블록에서 거래 데이터 추출.

    Args:
        block: 인자.

    Raises:
        없음.

    Example:
        >>> parseRevenueTxBlock(...)
    """
    dataRows = [line for line in block if not isSeparatorRow(line)]
    results = []

    for row in dataRows:
        cells = splitCells(row)
        if len(cells) < 3:
            continue
        if any("단위" in c for c in cells):
            continue
        if any(c in ("회사명", "법인명", "거래상대방", "구분") for c in cells[:2]):
            continue

        entity = cells[0].strip()
        if not entity or entity in ("-", ""):
            continue

        amounts = []
        for cell in cells[1:]:
            val = parseAmount(cell)
            if val is not None:
                amounts.append(val)

        if amounts:
            results.append(
                {
                    "entity": entity,
                    "sales": amounts[0] if len(amounts) >= 1 else None,
                    "purchases": amounts[1] if len(amounts) >= 2 else None,
                }
            )

    return results


# pipeline
def relatedPartyTx(stockCode: str) -> RelatedPartyTxResult | None:
    """사업보고서에서 대주주 거래 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        RelatedPartyTxResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> relatedPartyTx(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)
    years = sorted(df["year"].unique().to_list(), reverse=True)

    guaranteeRows: list[dict] = []
    revenueTxRows: list[dict] = []

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        content = _findSection(report)
        if content is None:
            continue

        blocks = extractTableBlocks(content)
        yearHasGuarantee = False
        yearHasRevenue = False

        for block in blocks:
            kind = classifyBlock(block)

            if kind == "guarantee" and not yearHasGuarantee:
                entries = parseGuaranteeBlock(block)
                for e in entries:
                    e["year"] = int(year)
                    guaranteeRows.append(e)
                if entries:
                    yearHasGuarantee = True

            elif kind == "revenueTx" and not yearHasRevenue:
                entries = parseRevenueTxBlock(block)
                for e in entries:
                    e["year"] = int(year)
                    revenueTxRows.append(e)
                if entries:
                    yearHasRevenue = True

    if not guaranteeRows and not revenueTxRows:
        return None

    guaranteeDf = _buildGuaranteeDf(guaranteeRows) if guaranteeRows else None
    revenueTxDf = _buildRevenueTxDf(revenueTxRows) if revenueTxRows else None

    yearSet = {r["year"] for r in guaranteeRows} | {r["year"] for r in revenueTxRows}

    return RelatedPartyTxResult(
        corpName=corpName,
        nYears=len(yearSet),
        guaranteeDf=guaranteeDf,
        revenueTxDf=revenueTxDf,
    )


def _findSection(report: pl.DataFrame) -> str | None:
    """대주주 거래 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if re.search(r"대주주.*거래|특수관계", title):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content
    return None


def _buildGuaranteeDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "entity": pl.Utf8,
        "amount": pl.Int64,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)


def _buildRevenueTxDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "entity": pl.Utf8,
        "sales": pl.Int64,
        "purchases": pl.Int64,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)
