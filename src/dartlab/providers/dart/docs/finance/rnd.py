"""연구개발활동 데이터 추출 파이프라인.

P2 통합: 기존 rnd/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class RndResult:
    """연구개발활동 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        rndDf: R&D 비용 시계열 DataFrame
            year | rndExpense | revenueRatio
    """

    corpName: str | None = None
    nYears: int = 0
    rndDf: pl.DataFrame | None = None


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
        return int(float(text))
    except ValueError:
        return None


def parseFloat(text: str) -> float | None:
    """퍼센트 등 소수 파싱.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseFloat(...)

    Returns:
        <TODO: return desc> (float | None)

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
    text = text.strip().replace(",", "").replace("%", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None
    try:
        return float(text)
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


def parseRndTable(block: list[str]) -> dict | None:
    """R&D 비용 테이블 파싱.

    구조 (삼성전자 등):
    | 과 목 | 제56기 | 제55기 | 제54기 |
    | 연구개발비용 계 | 35,021,531 | 28,352,769 | 24,929,171 |
    | (정부보조금) | ... | ... | ... |
    | 연구개발비/매출액 비율 | 11.45% | 10.88% | 9.67% |

    Returns:
        {"periods": [...], "rndExpense": [...], "revenueRatio": [...]}

    Raises:
        없음.

    Example:
        >>> parseRndTable(...)

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
        return None

    # R&D 관련 테이블인지 확인
    blockText = " ".join(dataRows)
    if "연구개발" not in blockText and "R&D" not in blockText:
        return None

    # 기간 헤더 찾기
    headerRow = None
    periods: list[str] = []
    for row in dataRows:
        cells = splitCells(row)
        periodCells = [c for c in cells if re.search(r"\d+기|당기|전기|\d{4}년", c)]
        if periodCells:
            headerRow = row
            periods = periodCells
            break

    if not periods:
        return None

    # 데이터 행 파싱
    rndExpense: list[int | None] = []
    revenueRatio: list[float | None] = []

    for row in dataRows:
        if row == headerRow:
            continue
        cells = splitCells(row)
        if len(cells) < 2:
            continue

        rowText = " ".join(cells[:3])

        # 연구개발비용 계
        if (
            ("연구개발비용" in rowText and "계" in rowText)
            or ("합 계" in rowText and "연구" in blockText)
            or ("연구개발비 합계" in rowText)
        ):
            for cell in cells:
                if re.match(r"^[\d,]+$", cell.strip()):
                    rndExpense.append(parseAmount(cell))

        # 매출액 대비 비율
        if "매출액" in rowText and ("비율" in rowText or "%" in " ".join(cells)):
            for cell in cells:
                val = parseFloat(cell)
                if val is not None and 0 < val < 100:
                    revenueRatio.append(val)

    if not rndExpense:
        return None

    return {
        "periods": periods,
        "rndExpense": rndExpense[: len(periods)],
        "revenueRatio": revenueRatio[: len(periods)] if revenueRatio else [],
    }


# pipeline
RND_SECTION_PATTERNS = [
    r"연구개발활동",
    r"연구개발",
    r"주요계약\s*및\s*연구개발",
]


def rnd(stockCode: str) -> RndResult | None:
    """사업보고서에서 연구개발비 시계열 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        RndResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> rnd(...)

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
            parsed = parseRndTable(block)
            if parsed and parsed["rndExpense"]:
                # 첫 번째 기간(당기) 값만 사용
                row: dict = {"year": int(year)}
                row["rndExpense"] = parsed["rndExpense"][0]
                if parsed["revenueRatio"]:
                    row["revenueRatio"] = parsed["revenueRatio"][0]
                allRows.append(row)
                break

    if not allRows:
        return None

    rndDf = _buildRndDf(allRows)

    return RndResult(
        corpName=corpName,
        nYears=len(allRows),
        rndDf=rndDf,
    )


def _findSection(report: pl.DataFrame) -> str | None:
    """연구개발 섹션 content 반환."""
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in RND_SECTION_PATTERNS):
            content = row.get("section_content", "") or ""
            if len(content) > 100:
                return content
    return None


def _buildRndDf(rows: list[dict]) -> pl.DataFrame:
    data = sorted(rows, key=lambda x: x["year"])
    schema = {
        "year": pl.Int64,
        "rndExpense": pl.Int64,
        "revenueRatio": pl.Float64,
    }
    for r in data:
        for col in schema:
            if col not in r:
                r[col] = None
    return pl.DataFrame(data, schema=schema)
