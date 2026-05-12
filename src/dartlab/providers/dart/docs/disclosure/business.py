"""사업의 내용 — 추출 파이프라인 + 파서 + 타입 (LoC 325, 룰 3 단일 .py)."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

import polars as pl

from dartlab.frame.dataLoader import extractCorpName, loadData
from dartlab.providers.reportSelector import extractReportYear, selectReport

SECTION_KEYS = {
    "overview": ["사업의 개요"],
    "products": ["주요 제품"],
    "materials": ["원재료", "생산 및 설비"],
    "sales": ["매출", "수주"],
    "risk": ["위험관리", "파생거래"],
    "rnd": ["주요계약", "연구개발", "경영상"],
    "etc": ["기타 참고"],
    "financial": ["재무건전성"],
}

_SPLIT_BY_NUMBER_RE = re.compile(r"^(\d+)\.\s+(.+?)$", re.MULTILINE)


@dataclass
class BusinessSection:
    """사업의 내용 하위 섹션."""

    key: str
    title: str
    chars: int
    text: str


@dataclass
class BusinessChange:
    """연도별 변경 정보."""

    year: int
    changedPct: float
    added: int
    removed: int
    totalChars: int


@dataclass
class BusinessResult:
    """사업의 내용 분석 결과.

    sections: 최신 연도의 섹션 목록 (하위 호환).
    yearSections: 연도별 전체 섹션 dict (LLM 다년도 비교용).
    """

    corpName: str | None
    year: int
    sections: list[BusinessSection] = field(default_factory=list)
    changes: list[BusinessChange] = field(default_factory=list)
    yearSections: dict[int, list[BusinessSection]] = field(default_factory=dict)


def classifySection(title: str) -> str | None:
    """섹션 타이틀을 키로 분류.

    Args:
        title: 인자.

    Raises:
        없음.

    Example:
        >>> classifySection(...)

    Returns:
        <TODO: return desc> (str | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    for key, keywords in SECTION_KEYS.items():
        for kw in keywords:
            if kw in title:
                return key
    return None


def extractFromSubSections(report: pl.DataFrame) -> dict[str, dict]:
    """하위 섹션이 분리된 경우 직접 매칭.

    Args:
        report: 인자.

    Raises:
        없음.

    Example:
        >>> extractFromSubSections(...)

    Returns:
        <TODO: return desc> (dict[str, dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    subSections = report.filter(
        pl.col("section_title").str.contains("사업의 개요")
        | pl.col("section_title").str.contains("주요 제품")
        | pl.col("section_title").str.contains("원재료")
        | pl.col("section_title").str.contains("생산 및 설비")
        | pl.col("section_title").str.contains("매출")
        | pl.col("section_title").str.contains("수주")
        | pl.col("section_title").str.contains("위험관리")
        | pl.col("section_title").str.contains("기타 참고")
        | pl.col("section_title").str.contains("연구개발")
        | pl.col("section_title").str.contains("주요계약")
        | pl.col("section_title").str.contains("경영상")
        | pl.col("section_title").str.contains("재무건전성")
    )

    if subSections.height == 0:
        return {}

    sections: dict[str, dict] = {}
    for row in subSections.iter_rows(named=True):
        title = row["section_title"]
        key = classifySection(title)
        if not key:
            continue
        content = row["section_content"]
        if key not in sections:
            sections[key] = {"title": title, "chars": len(content), "text": content}
        else:
            sections[key]["title"] += f" + {title}"
            sections[key]["chars"] += len(content)
            sections[key]["text"] += "\n\n" + content

    return sections


def extractFromUnified(report: pl.DataFrame) -> dict[str, dict]:
    """통합 텍스트에서 번호 패턴으로 분리.

    Args:
        report: 인자.

    Raises:
        없음.

    Example:
        >>> extractFromUnified(...)

    Returns:
        <TODO: return desc> (dict[str, dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    mainSection = report.filter(pl.col("section_title").str.contains("사업의 내용"))
    if mainSection.height == 0:
        return {}

    fullText = mainSection.row(0, named=True)["section_content"]
    chunks = splitByNumber(fullText)

    sections: dict[str, dict] = {}
    for num, title, text in chunks:
        key = classifySection(title)
        if key:
            sections[key] = {
                "title": f"{num}. {title}",
                "chars": len(text),
                "text": text,
            }

    return sections


def splitByNumber(text: str) -> list[tuple[str, str, str]]:
    """텍스트를 순차 번호 패턴으로 분리.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> splitByNumber(...)

    Returns:
        <TODO: return desc> (list[tuple[str, str, str]])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    allMatches = list(_SPLIT_BY_NUMBER_RE.finditer(text))

    topMatches = []
    expectedNum = 1
    for m in allMatches:
        num = int(m.group(1))
        if num == expectedNum:
            topMatches.append(m)
            expectedNum = num + 1
        elif num == 1 and expectedNum > 2:
            break

    chunks = []
    for i, m in enumerate(topMatches):
        num = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = topMatches[i + 1].start() if i + 1 < len(topMatches) else len(text)
        body = text[start:end].strip()
        chunks.append((num, title, body))

    return chunks


def getBusinessText(report: pl.DataFrame) -> str | None:
    """보고서에서 사업 개요 텍스트 추출 (변경 탐지용).

    Args:
        report: 인자.

    Raises:
        없음.

    Example:
        >>> getBusinessText(...)

    Returns:
        <TODO: return desc> (str | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    overview = report.filter(
        pl.col("section_title").str.starts_with("1.") & pl.col("section_title").str.contains("사업의 개요")
    )
    if overview.height > 0:
        return overview.row(0, named=True)["section_content"]

    main = report.filter(pl.col("section_title").str.contains("사업의 내용"))
    if main.height > 0:
        return main.row(0, named=True)["section_content"]

    return None


def computeChanges(df: pl.DataFrame, years: list[str]) -> list[dict]:
    """연도별 사업 내용 변경률 계산.

    Args:
        df: 인자.
        years: 인자.

    Raises:
        없음.

    Example:
        >>> computeChanges(...)

    Returns:
        <TODO: return desc> (list[dict])

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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
    changes = []
    prevText = None

    for year in years:
        annual = df.filter(
            (pl.col("year") == year)
            & pl.col("report_type").str.contains("사업보고서")
            & ~pl.col("report_type").str.contains("기재정정|첨부")
        )
        if annual.height == 0:
            continue

        overview = annual.filter(
            pl.col("section_title").str.starts_with("1.") & pl.col("section_title").str.contains("사업의 개요")
        )
        if overview.height > 0:
            text = overview.row(0, named=True)["section_content"]
        else:
            main = annual.filter(pl.col("section_title").str.contains("사업의 내용"))
            if main.height > 0:
                text = main.row(0, named=True)["section_content"]
            else:
                continue

        if prevText is not None:
            ratio = difflib.SequenceMatcher(None, prevText, text).ratio()
            changedPct = round((1 - ratio) * 100, 1)

            diffLines = list(difflib.unified_diff(prevText.splitlines(), text.splitlines(), lineterm="", n=0))
            added = sum(1 for l in diffLines if l.startswith("+") and not l.startswith("+++"))
            removed = sum(1 for l in diffLines if l.startswith("-") and not l.startswith("---"))

            changes.append(
                {
                    "year": int(year),
                    "changedPct": changedPct,
                    "added": added,
                    "removed": removed,
                    "totalChars": len(text),
                }
            )

        prevText = text

    return changes


def business(stockCode: str) -> BusinessResult | None:
    """사업보고서에서 사업의 내용 섹션 추출 + 연도별 변경 탐지.

    Args:
        stockCode: 종목코드 (6자리).

    Returns:
        BusinessResult 또는 데이터 부족 시 None.

    Example:
        >>> business("005930")  # 삼성전자

    Raises:
        없음.

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - difflib
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

    allSections: dict[int, list[BusinessSection]] = {}
    latestYear: int | None = None

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        reportYear = extractReportYear(report["report_type"][0])
        if reportYear is None:
            continue

        sections = extractFromSubSections(report)
        if not sections:
            sections = extractFromUnified(report)

        if sections and reportYear not in allSections:
            sectionList = [
                BusinessSection(
                    key=key,
                    title=info["title"],
                    chars=info["chars"],
                    text=info["text"],
                )
                for key, info in sections.items()
            ]
            allSections[reportYear] = sectionList
            if latestYear is None:
                latestYear = reportYear

    if not allSections or latestYear is None:
        return None

    allYears = sorted(df["year"].unique().to_list())
    rawChanges = computeChanges(df, allYears)
    changeList = [
        BusinessChange(
            year=c["year"],
            changedPct=c["changedPct"],
            added=c["added"],
            removed=c["removed"],
            totalChars=c["totalChars"],
        )
        for c in rawChanges
    ]

    return BusinessResult(
        corpName=corpName,
        year=latestYear,
        sections=allSections[latestYear],
        changes=changeList,
        yearSections=allSections,
    )
