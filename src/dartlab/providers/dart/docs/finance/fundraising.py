"""증권 발행(증자/감자) 파이프라인.

P2 통합: 기존 fundraising/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class FundraisingResult:
    """증권 발행(증자/감자) 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        issuances: 발행 이력 [{date, issueType, stockType, quantity, parValue, issuePrice, note}, ...]
        noData: 발행 실적 없음 여부
        issuanceDf: 발행 이력 DataFrame
            date | issueType | stockType | quantity | parValue | issuePrice | note
    """

    corpName: str | None = None
    nYears: int = 0
    issuances: list[dict] = field(default_factory=list)
    noData: bool = False
    issuanceDf: pl.DataFrame | None = None


# parser
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


def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseAmount(...)

    Returns:
        int | None — 결과.
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


def parseEquityIssuance(content: str) -> list[dict]:
    """증자(감자) 현황 테이블 파싱.

    | 주식발행(감소)일자 | 발행(감소)형태 | 종류 | 수량 | 주당액면가액 | 주당발행(감소)가액 | 비고 |
    | 2020.01.03 | 전환권행사 | 보통주 | 92,603 | 500 | 118,786 | 발행회차: 제 10회 |
    | 2010년 06월 15일 | 신주인수권행사 | 보통주 | 874,916 | 500 | 598 | - |

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseEquityIssuance(...)

    Returns:
        list[dict] — 결과.
    """
    lines = content.split("\n")
    results: list[dict] = []

    # 증자(감자) 테이블 영역 찾기
    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        # 섹션 시작 감지
        if "증자" in stripped and ("감자" in stripped or "현황" in stripped):
            inSection = True
            continue

        # 채무증권 섹션이 시작되면 종료
        if "채무증권" in stripped:
            break

        if not inSection:
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)

        # 헤더 행 건너뛰기
        if any("발행" in c and ("일자" in c or "형태" in c) for c in cells):
            headerFound = True
            continue
        if any(c in ("종류", "수량", "주당액면가액") for c in cells):
            continue

        if not headerFound:
            continue

        # 기준일/단위 행 건너뛰기
        if any("기준일" in c or "단위" in c for c in cells):
            continue

        # 데이터 행: 최소 4열 이상, 첫 셀이 날짜 패턴
        if len(cells) < 4:
            continue

        dateStr = cells[0].strip()
        # 날짜 패턴: YYYY.MM.DD or YYYY-MM-DD or YYYY/MM/DD or YYYY년 MM월 DD일
        dateMatch = re.match(r"^(\d{4})[\.\-/](\d{2})[\.\-/](\d{2})$", dateStr)
        if not dateMatch:
            dateMatch = re.match(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일$", dateStr)
        if not dateMatch:
            continue

        # 날짜 정규화: YYYY.MM.DD
        normalizedDate = f"{dateMatch.group(1)}.{int(dateMatch.group(2)):02d}.{int(dateMatch.group(3)):02d}"

        # 파싱
        entry = {"date": normalizedDate}

        if len(cells) > 1:
            entry["issueType"] = cells[1].strip()
        if len(cells) > 2:
            entry["stockType"] = cells[2].strip()
        if len(cells) > 3:
            entry["quantity"] = parseAmount(cells[3])
        if len(cells) > 4:
            entry["parValue"] = parseAmount(cells[4])
        if len(cells) > 5:
            entry["issuePrice"] = parseAmount(cells[5])
        if len(cells) > 6:
            entry["note"] = cells[6].strip()

        results.append(entry)

    return results


# pipeline
def fundraising(stockCode: str) -> FundraisingResult | None:
    """증권 발행(증자/감자) 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> fundraising(...)

    Returns:
        FundraisingResult | None — 결과.
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
            if "증권" in title and "자금조달" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                issuances = parseEquityIssuance(content)

                if not issuances:
                    noDataSignals = (
                        "없습니다" in content[:500]
                        or "해당사항 없음" in content[:500]
                        or "해당없음" in content[:500]
                        or len(content) < 300
                    )
                    hasHeader = "발행" in content and ("일자" in content or "형태" in content)
                    if noDataSignals or hasHeader:
                        return FundraisingResult(
                            corpName=corpName,
                            nYears=1,
                            issuances=[],
                            noData=True,
                        )
                    continue

                issuanceDf = pl.DataFrame(
                    {
                        "date": [i.get("date", "") for i in issuances],
                        "issueType": [i.get("issueType", "") for i in issuances],
                        "stockType": [i.get("stockType", "") for i in issuances],
                        "quantity": [i.get("quantity") for i in issuances],
                        "parValue": [i.get("parValue") for i in issuances],
                        "issuePrice": [i.get("issuePrice") for i in issuances],
                        "note": [i.get("note", "") for i in issuances],
                    },
                    schema={
                        "date": pl.Utf8,
                        "issueType": pl.Utf8,
                        "stockType": pl.Utf8,
                        "quantity": pl.Int64,
                        "parValue": pl.Int64,
                        "issuePrice": pl.Int64,
                        "note": pl.Utf8,
                    },
                )

                return FundraisingResult(
                    corpName=corpName,
                    nYears=1,
                    issuances=issuances,
                    noData=False,
                    issuanceDf=issuanceDf,
                )

    return None
