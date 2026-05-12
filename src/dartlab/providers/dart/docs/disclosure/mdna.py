"""이사의 경영진단 및 분석의견 (MD&A) — 추출 파이프라인 + 파서 + 타입 (룰 3 단일 .py)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import extractReportYear, selectReport

KOREAN_NUMS = {
    "가": 1,
    "나": 2,
    "다": 3,
    "라": 4,
    "마": 5,
    "바": 6,
    "사": 7,
    "아": 8,
    "자": 9,
    "차": 10,
}

SECTION_ALIASES = {
    "overview": ["개요", "영업상황"],
    "forecast": ["예측정보"],
    "financials": ["재무상태", "영업실적", "경영성과"],
    "liquidity": ["유동성", "자금조달"],
    "offBalance": ["부외거래", "부외 거래"],
    "other": ["그 밖에", "그 밖의", "투자의사결정", "투자결정"],
    "accounting": ["회계정책", "회계추정"],
    "regulation": ["법규상", "규제"],
    "derivative": ["파생상품", "위험관리"],
    "strategy": ["추진 전략", "사업전망"],
}


@dataclass
class MdnaSection:
    """MD&A 개별 섹션."""

    title: str
    category: str
    text: str
    textLines: int = 0
    tableLines: int = 0


@dataclass
class MdnaResult:
    """이사의 경영진단 및 분석의견 분석 결과."""

    corpName: str | None
    nYears: int
    sections: list[MdnaSection] = field(default_factory=list)
    overview: str | None = None


def _isSectionHeader(line: str) -> tuple[int, str] | None:
    s = line.strip()

    m = re.match(r"^(\d{1,2})\.\s+(.+)", s)
    if m:
        num = int(m.group(1))
        title = m.group(2).strip()
        if num <= 20 and len(title) >= 2:
            return (num, title)

    m = re.match(r"^([가-차])\.\s+(.+)", s)
    if m:
        char = m.group(1)
        title = m.group(2).strip()
        if char in KOREAN_NUMS and len(title) >= 2:
            return (KOREAN_NUMS[char], title)

    return None


def classifySection(title: str) -> str:
    """MD&A 섹션 타이틀을 카테고리 키로 분류.

    Args:
        title: 섹션 헤더 텍스트 (예: ``"1. 개요"``).

    Returns:
        SECTION_ALIASES 의 키 (overview/forecast/financials...) 또는 ``"unknown"``.

    Example:
        >>> classifySection("1. 개요")
        'overview'

    Raises:
        없음.

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
    for key, keywords in SECTION_ALIASES.items():
        for kw in keywords:
            if kw in title:
                return key
    return "unknown"


def parseMdna(content: str) -> dict[str, str]:
    """MD&A 콘텐츠를 섹션별로 분리.

    Args:
        content: 사업보고서 의 MD&A 섹션 원문 텍스트.

    Returns:
        ``{sectionTitle: sectionContent}`` 딕셔너리.
        예: ``{"1. 예측정보에 대한 주의사항": "...", "2. 개요": "..."}``.

    Example:
        >>> parseMdna("1. 개요\\n...\\n2. 재무상태\\n...")

    Raises:
        없음.

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
    sections: dict[str, str] = {}
    currentKey = None
    currentLines: list[str] = []

    for line in lines:
        s = line.strip()

        if s.startswith("IV.") or s.startswith("V."):
            continue

        header = _isSectionHeader(s)
        if header:
            num, title = header
            if currentKey and currentLines:
                sections[currentKey] = "\n".join(currentLines)
            currentKey = f"{num}. {title}"
            currentLines = []
            continue

        if currentKey is not None:
            currentLines.append(line)

    if currentKey and currentLines:
        sections[currentKey] = "\n".join(currentLines)

    return sections


def extractOverview(sections: dict[str, str]) -> str | None:
    """섹션 딕셔너리에서 개요 텍스트 추출.

    Args:
        sections: 인자.

    Raises:
        없음.

    Example:
        >>> extractOverview(...)

    Returns:
        <TODO: return desc> (str | None)

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
    for key, content in sections.items():
        if classifySection(key) == "overview":
            textLines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("|")]
            result = "\n".join(textLines).strip()
            return result or None
    return None


def mdna(stockCode: str) -> MdnaResult | None:
    """사업보고서에서 이사의 경영진단 및 분석의견 (MD&A) 추출.

    Args:
        stockCode: 종목코드 (6자리).

    Returns:
        MdnaResult 또는 데이터 부족 시 None.

    Example:
        >>> mdna("005930")  # 삼성전자

    Raises:
        없음.

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

    yearSections: dict[int, dict[str, str]] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        mdnaRows = report.filter(pl.col("section_title").str.contains("경영진단"))
        if mdnaRows.height == 0:
            continue

        reportYear = extractReportYear(mdnaRows["report_type"][0])
        if reportYear is None:
            continue

        content = mdnaRows["section_content"][0]
        sections = parseMdna(content)

        if sections and reportYear not in yearSections:
            yearSections[reportYear] = sections

    if not yearSections:
        return None

    latestYear = max(yearSections.keys())
    latestSections = yearSections[latestYear]

    sectionList = []
    for title, content in latestSections.items():
        category = classifySection(title)
        textLines = [l for l in content.split("\n") if l.strip() and not l.strip().startswith("|")]
        tableLines = [l for l in content.split("\n") if l.strip().startswith("|")]
        sectionList.append(
            MdnaSection(
                title=title,
                category=category,
                text=content,
                textLines=len(textLines),
                tableLines=len(tableLines),
            )
        )

    overview = extractOverview(latestSections)

    return MdnaResult(
        corpName=corpName,
        nYears=len(yearSections),
        sections=sectionList,
        overview=overview,
    )
