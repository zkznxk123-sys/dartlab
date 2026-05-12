"""매출 및 수주상황 파이프라인.

P2 통합: 기존 salesOrder/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class SalesOrderResult:
    """매출 및 수주상황 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        unit: 단위 (억원, 백만원 등)
        sales: 매출실적 [{label, values}, ...]
        orders: 수주상황 [{label, values}, ...]
        noData: 해당사항 없음 여부
        salesDf: 매출실적 DataFrame (label | v1 | v2 | v3)
        orderDf: 수주상황 DataFrame (label | v1 | v2 | ...)
    """

    corpName: str | None = None
    nYears: int = 0
    unit: str = "백만원"
    sales: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    noData: bool = False
    salesDf: pl.DataFrame | None = None
    orderDf: pl.DataFrame | None = None


# parser
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


def parseAmount(text: str) -> int | None:
    """숫자 문자열을 정수로 변환. △는 음수.

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
    if text in ("-", "−", "–", ""):
        return None

    negative = False
    if text.startswith("△") or text.startswith("(") or text.startswith("−"):
        negative = True
        text = text.lstrip("△(−").rstrip(")")

    text = text.replace(",", "").replace(" ", "")
    text = re.sub(r"[^\d.]", "", text)
    if not text:
        return None
    try:
        val = int(float(text))
        if abs(val) > 9_000_000_000_000_000_000:
            return None
        return -val if negative else val
    except (ValueError, OverflowError):
        return None


def detectUnit(content: str) -> str:
    """단위 감지.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> detectUnit(...)

    Returns:
        <TODO: return desc> (str)

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
    m = re.search(r"단위\s*[:\s]*\s*(백만원|억원|천원|원)", content[:500])
    if m:
        return m.group(1)
    return "백만원"


def _isHeaderRow(cells: list[str]) -> bool:
    """헤더 행 판별."""
    keywords = {
        "구분",
        "부문",
        "매출유형",
        "품목",
        "품 목",
        "주요제품",
        "사업구분",
        "매출액",
        "비중",
        "금액",
        "내수",
        "수출",
        "합계",
        "합 계",
        "제품",
        "상품",
        "용역",
    }
    return sum(1 for c in cells if c.strip() in keywords or "기" in c or "년" in c) >= 2


def _extractValueHeaders(headerCols: list[str]) -> list[str]:
    """헤더 행에서 숫자 값에 대응하는 컬럼명만 추출.

    라벨 역할의 키워드(구분, 부문 등)를 제외하고 기(期)/년 등
    시간축 헤더를 반환한다.
    """
    labelKeywords = {
        "구분",
        "부문",
        "매출유형",
        "품목",
        "품 목",
        "주요제품",
        "사업구분",
        "제품",
        "상품",
        "용역",
    }
    valueHeaders = []
    for c in headerCols:
        s = c.strip()
        if not s or s in labelKeywords:
            continue
        if re.match(r"^\d+\.?\d*%$", s):
            continue
        valueHeaders.append(s)
    return valueHeaders


def parseSalesTable(content: str) -> tuple[list[dict], list[str]]:
    """매출실적 테이블 파싱.

    Returns:
        (rows, valueHeaders) 튜플.
        valueHeaders는 값 컬럼의 헤더명 목록 (예: ["제47기", "제46기"]).

    Raises:
        없음.

    Args:
        content: <TODO: param desc> (str)

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

    inSection = False
    headerCols: list[str] = []
    skipCount = 0

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if re.search(r"매출\s*실적|매출\s*현황|부문별\s*매출", stripped):
                inSection = True
            continue

        if re.search(r"판매경로|판매방법|판매전략|수주상황|수주 상황|나\.\s", stripped) and "|" not in stripped:
            break

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        if any("단위" in c or "기준일" in c for c in cells):
            continue

        if not headerCols and _isHeaderRow(cells):
            headerCols = cells
            continue

        if headerCols and skipCount < 1 and _isHeaderRow(cells):
            skipCount += 1
            continue

        if not headerCols:
            continue

        nums = [parseAmount(c) for c in cells]
        hasNum = sum(1 for n in nums if n is not None)
        if hasNum < 1:
            continue

        label_parts = []
        values = []
        for c in cells:
            val = parseAmount(c)
            if val is not None:
                values.append(val)
            elif c.strip() and c.strip() not in ("-", "−", "–"):
                if re.match(r"^\d+\.?\d*%$", c.strip()):
                    continue
                label_parts.append(c.strip())

        if not label_parts:
            continue

        label = " > ".join(label_parts)
        results.append({"label": label, "values": values})

    valueHeaders = _extractValueHeaders(headerCols) if headerCols else []
    return results, valueHeaders


def parseOrderBacklog(content: str) -> tuple[list[dict], list[str]]:
    """수주상황 테이블 파싱.

    Returns:
        (rows, valueHeaders) 튜플.

    Raises:
        없음.

    Example:
        >>> parseOrderBacklog(...)

    Args:
        content: <TODO: param desc> (str)

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

    inSection = False
    headerCols: list[str] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if "수주상황" in stripped or "수주 상황" in stripped:
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        if any("수주" in c and ("총액" in c or "잔고" in c) for c in cells):
            headerCols = cells
            headerFound = True
            continue

        if not headerFound:
            continue

        if any("단위" in c or "기준일" in c for c in cells):
            continue

        nums = [parseAmount(c) for c in cells]
        hasNum = sum(1 for n in nums if n is not None)
        if hasNum < 1:
            continue

        label_parts = []
        values = []
        for c in cells:
            val = parseAmount(c)
            if val is not None:
                values.append(val)
            elif c.strip() and c.strip() not in ("-", "−", "–"):
                label_parts.append(c.strip())

        if not label_parts:
            continue

        results.append({"label": " > ".join(label_parts), "values": values})

    valueHeaders = _extractValueHeaders(headerCols) if headerCols else []
    return results, valueHeaders


# pipeline
def _buildDf(rows: list[dict], headers: list[str] | None = None) -> pl.DataFrame | None:
    """행 목록을 DataFrame으로 변환.

    headers가 제공되면 v1/v2/v3 대신 실제 헤더명을 컬럼명으로 사용한다.
    """
    if not rows:
        return None

    maxVals = max(len(r["values"]) for r in rows)
    data: dict[str, list] = {"label": [r["label"] for r in rows]}
    for i in range(maxVals):
        colName = headers[i] if headers and i < len(headers) else f"v{i + 1}"
        if colName in data:
            colName = f"{colName}_{i + 1}"
        data[colName] = [r["values"][i] if i < len(r["values"]) else None for r in rows]

    schema = {"label": pl.Utf8}
    for col in data:
        if col != "label":
            schema[col] = pl.Int64

    return pl.DataFrame(data, schema=schema)


def salesOrder(stockCode: str) -> SalesOrderResult | None:
    """매출 및 수주상황 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> salesOrder(...)

    Returns:
        <TODO: return desc> (SalesOrderResult | None)

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
            if "매출" in title and ("수주" in title or "사항" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = detectUnit(content)
                sales, salesHeaders = parseSalesTable(content)
                orders, orderHeaders = parseOrderBacklog(content)

                if not sales and not orders:
                    if "없습니다" in content[:500] or len(content) < 300:
                        return SalesOrderResult(
                            corpName=corpName,
                            nYears=1,
                            unit=unit,
                            noData=True,
                        )
                    continue

                return SalesOrderResult(
                    corpName=corpName,
                    nYears=1,
                    unit=unit,
                    sales=sales,
                    orders=orders,
                    noData=False,
                    salesDf=_buildDf(sales, salesHeaders),
                    orderDf=_buildDf(orders, orderHeaders),
                )

    return None
