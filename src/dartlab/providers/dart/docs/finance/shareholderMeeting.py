"""주주총회 등에 관한 사항 파이프라인.

P2 통합: 기존 shareholderMeeting/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.frame.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class ShareholderMeetingResult:
    """주주총회 등에 관한 사항 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    agendas: list[dict] = field(default_factory=list)
    textOnly: bool = False
    agendaDf: pl.DataFrame | None = None


# parser
def splitCells(line: str) -> list[str]:
    """파이프(|)로 구분된 셀을 분리.

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
    """구분선 행인지 확인.

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


def parseAmount(text: str) -> int | None:
    """금액 문자열을 정수로 변환.

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
    text = re.sub(r"[^\d]", "", text)
    if not text:
        return None
    try:
        return int(text)
    except (ValueError, OverflowError):
        return None


def parseMeetingAgenda(content: str) -> list[dict]:
    """주주총회 안건 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseMeetingAgenda(...)

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
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        # 헤더 감지
        if any("안건" in c or "의안" in c or "부의안건" in c for c in cells) and any(
            "결과" in c or "가결" in c or "찬성" in c or "내용" in c for c in cells
        ):
            headerFound = True
            continue

        if any("구분" in c or "구 분" in c for c in cells) and any("안건" in c or "내용" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 데이터 행
        label = ""
        for c in cells:
            if len(c.strip()) >= 3 and parseAmount(c) is None:
                label = c.strip()
                break

        if not label:
            continue

        entry: dict = {"agenda": label}
        # 결과 찾기
        for c in cells:
            if "가결" in c or "승인" in c or "원안" in c:
                entry["result"] = c.strip()
                break
            elif "부결" in c:
                entry["result"] = c.strip()
                break

        results.append(entry)

    return results


# pipeline
def shareholderMeeting(stockCode: str) -> ShareholderMeetingResult | None:
    """주주총회 등에 관한 사항 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> shareholderMeeting(...)

    Returns:
        <TODO: return desc> (ShareholderMeetingResult | None)

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
            if "주주총회" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                agendas = parseMeetingAgenda(content)
                if agendas:
                    agendaDf = pl.DataFrame(agendas)
                    return ShareholderMeetingResult(
                        corpName=corpName,
                        nYears=1,
                        agendas=agendas,
                        agendaDf=agendaDf,
                    )

                if len(content) > 200:
                    return ShareholderMeetingResult(
                        corpName=corpName,
                        nYears=1,
                        textOnly=True,
                    )
    return None
