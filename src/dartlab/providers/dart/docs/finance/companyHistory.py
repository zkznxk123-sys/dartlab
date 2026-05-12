"""회사의 연혁 — 공시 본문 "회사의 연혁" 섹션 파싱 + dataclass 반환.

P2 통합: 기존 companyHistory/{parser,pipeline,types}.py 단일 모듈로 흡수 (122 LoC).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import selectReport

if TYPE_CHECKING:
    pass


@dataclass
class CompanyHistoryResult:
    """회사의 연혁 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    events: list[dict] = field(default_factory=list)
    eventsDf: pl.DataFrame | None = None


def splitCells(line: str) -> list[str]:
    """파이프 구분자로 셀 분리.

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
    """구분선 행 여부 확인.

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


def parseHistory(content: str) -> list[dict]:
    """연혁 테이블 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseHistory(...)

    Returns:
        <TODO: return desc> (list[dict])

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
    results: list[dict] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        # 헤더 감지
        if any("일자" in c or "연월" in c or "날짜" in c or "년월" in c for c in cells) and any(
            "내용" in c or "연혁" in c or "사항" in c or "내역" in c for c in cells
        ):
            headerFound = True
            continue

        if not headerFound:
            # 날짜 패턴이 있으면 헤더 없이도 파싱
            if re.search(r"\d{4}[년.]\s*\d{1,2}", cells[0]):
                headerFound = True
            else:
                continue

        date = cells[0].strip()
        if not date or not re.search(r"\d{4}", date):
            continue

        event = cells[1].strip() if len(cells) >= 2 else ""
        if not event or len(event) < 2:
            continue

        results.append({"date": date, "event": event})

    return results


def companyHistory(stockCode: str) -> CompanyHistoryResult | None:
    """회사의 연혁 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> companyHistory(...)

    Returns:
        <TODO: return desc> (CompanyHistoryResult | None)

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
            if "연혁" in title and ("회사" in title or title.strip().endswith("연혁")):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                events = parseHistory(content)
                if events:
                    eventsDf = pl.DataFrame(events)
                    return CompanyHistoryResult(
                        corpName=corpName,
                        nYears=1,
                        events=events,
                        eventsDf=eventsDf,
                    )
    return None
