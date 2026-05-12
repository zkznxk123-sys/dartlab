"""기타 재무에 관한 사항 파이프라인.

P2 통합: 기존 otherFinance/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class OtherFinanceResult:
    """기타 재무에 관한 사항 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    badDebt: list[dict] = field(default_factory=list)
    inventory: list[dict] = field(default_factory=list)
    noData: bool = False
    badDebtDf: pl.DataFrame | None = None
    inventoryDf: pl.DataFrame | None = None


# parser
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
    text = text.strip()
    if text in ("-", "\u2212", "\u2013", ""):
        return None
    negative = False
    if text.startswith("\u25b3") or text.startswith("(") or text.startswith("\u2212"):
        negative = True
        text = text.lstrip("\u25b3(\u2212").rstrip(")")
    text = text.replace(",", "").replace(" ", "")
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        return -val if negative else val
    except (ValueError, OverflowError):
        return None


def parseBadDebtProvision(content: str) -> list[dict]:
    """대손충당금 설정내역 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseBadDebtProvision(...)

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
    currentPeriod = ""

    for line in lines:
        stripped = line.strip()
        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        # 단위 행 스킵
        if any("단위" in c for c in cells) and len(cells) <= 2:
            continue

        # 헤더 감지
        if any("계정과목" in c for c in cells) and any("대손충당금" in c or "충당금" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 변동현황 테이블 시작시 중단
        if any("기초" in c and "잔액" in c for c in cells):
            break
        if any("변동" in c for c in cells) and any("현황" in c for c in cells):
            break

        # 기수 감지 (제96기, 제95기 등)
        periodMatch = re.search(r"제\d+기", cells[0])
        if periodMatch:
            currentPeriod = periodMatch.group()

        # 숫자가 있는 셀 찾기
        nums = [parseAmount(c) for c in cells]
        validNums = [n for n in nums if n is not None]

        if not validNums:
            continue

        # 계정과목 찾기
        account = ""
        for c in cells:
            if parseAmount(c) is None and c.strip() and c.strip() not in ("-", "\u2212", "\u2013"):
                cleaned = re.sub(r"제\d+기", "", c).strip()
                if cleaned and len(cleaned) >= 2:
                    account = cleaned
                    break

        if not account:
            continue

        entry: dict = {"account": account}
        if currentPeriod:
            entry["period"] = currentPeriod
        if len(validNums) >= 1:
            entry["totalDebt"] = validNums[0]
        if len(validNums) >= 2:
            entry["provision"] = validNums[1]

        results.append(entry)

    return results


def parseInventory(content: str) -> list[dict]:
    """재고자산 현황 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseInventory(...)

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
    inSection = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if "재고자산" in stripped and ("현황" in stripped or "내역" in stripped):
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        if any("단위" in c for c in cells) and len(cells) <= 2:
            continue

        if any("구 분" in c or "구분" in c or "계정과목" in c for c in cells) and any(
            "금액" in c or "당기" in c or "기말" in c for c in cells
        ):
            headerFound = True
            continue

        if not headerFound:
            continue

        # 숫자 찾기
        nums = [parseAmount(c) for c in cells]
        validNums = [n for n in nums if n is not None]
        if not validNums:
            continue

        label = ""
        for c in cells:
            if parseAmount(c) is None and c.strip() and c.strip() not in ("-", "\u2212", "\u2013"):
                if len(c.strip()) >= 2:
                    label = c.strip()
                    break

        if not label:
            continue

        entry = {"item": label, "values": validNums}
        results.append(entry)

    return results


# pipeline
def otherFinance(stockCode: str) -> OtherFinanceResult | None:
    """기타 재무에 관한 사항 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> otherFinance(...)

    Returns:
        <TODO: return desc> (OtherFinanceResult | None)

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
            if "기타 재무" in title or ("기타" in title and "재무" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                badDebt = parseBadDebtProvision(content)
                inventory = parseInventory(content)

                if not badDebt and not inventory:
                    if "해당사항" in content[:500] or "없습니다" in content[:500] or "참조" in content[:300]:
                        return OtherFinanceResult(corpName=corpName, nYears=1, noData=True)
                    continue

                badDebtDf = None
                if badDebt:
                    badDebtDf = pl.DataFrame(badDebt)

                inventoryDf = None
                if inventory:
                    inventoryDf = pl.DataFrame(inventory)

                return OtherFinanceResult(
                    corpName=corpName,
                    nYears=1,
                    badDebt=badDebt,
                    inventory=inventory,
                    badDebtDf=badDebtDf,
                    inventoryDf=inventoryDf,
                )
    return None
