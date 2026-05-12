"""주요 제품 및 서비스 파이프라인.

P2 통합: 기존 productService/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.core.reportSelector import selectReport

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class ProductServiceResult:
    """주요 제품 및 서비스 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        unit: 단위 (억원, 백만원 등)
        products: 제품/서비스 목록 [{label, amount, ratio}, ...]
        noData: 해당사항 없음 여부
        productDf: 제품/서비스 DataFrame (label | amount | ratio)
    """

    corpName: str | None = None
    nYears: int = 0
    unit: str = "백만원"
    products: list[dict] = field(default_factory=list)
    noData: bool = False
    productDf: pl.DataFrame | None = None


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


def parseRatio(text: str) -> float | None:
    """비중(%) 문자열을 float로 변환.

    Args:
        text: 인자.

    Raises:
        없음.

    Example:
        >>> parseRatio(...)

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
    text = text.strip().replace("%", "").replace(",", "").replace(" ", "")
    if text in ("-", "−", "–", ""):
        return None

    negative = False
    if text.startswith("△") or text.startswith("(") or text.startswith("−"):
        negative = True
        text = text.lstrip("△(−").rstrip(")")

    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
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


def parseProductService(content: str) -> list[dict]:
    """주요 제품/서비스 테이블 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseProductService(...)

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
    inTable = False
    nonTableGap = 0

    for line in lines:
        stripped = line.strip()

        if "|" not in stripped or isSeparatorRow(stripped):
            if inTable:
                nonTableGap += 1
                if nonTableGap > 2:
                    break
            continue

        nonTableGap = 0
        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        if any("단위" in c for c in cells):
            continue

        if any("※" in c or "참고" in c or "참조" in c for c in cells):
            if inTable and results:
                break
            continue

        if any("가격" in c and "변동" in c for c in cells):
            break

        if not headerFound:
            hasProduct = any(
                k in c
                for c in cells
                for k in (
                    "제품",
                    "서비스",
                    "품목",
                    "품 목",
                    "구분",
                    "부문",
                    "부 문",
                    "사업부문",
                    "상품명",
                    "사업영역",
                )
            )
            hasMoney = any(k in c for c in cells for k in ("매출", "금액", "비중", "비율"))
            if hasProduct and hasMoney:
                headerFound = True
                continue
            if hasProduct or hasMoney:
                headerFound = True
                continue

        if not headerFound:
            continue

        if all(c.strip() in ("매출액", "비중", "비율", "금액", "") for c in cells):
            continue

        inTable = True

        label_parts = []
        amount = None
        ratio = None

        for c in cells:
            c_stripped = c.strip()
            if not c_stripped:
                continue

            if "%" in c_stripped:
                if ratio is None:
                    ratio = parseRatio(c_stripped)
                continue

            parsed = parseAmount(c_stripped)
            if parsed is not None and abs(parsed) > 10:
                if amount is None:
                    amount = parsed
                continue

            try:
                fval = float(c_stripped.replace(",", ""))
                if 0 < abs(fval) <= 100 and "." in c_stripped:
                    if ratio is None:
                        ratio = fval
                    continue
            except ValueError:
                pass

            label_parts.append(c_stripped)

        if not label_parts:
            continue

        label = " > ".join(label_parts)

        entry = {"label": label}
        if amount is not None:
            entry["amount"] = amount
        if ratio is not None:
            entry["ratio"] = ratio
        results.append(entry)

    return results


# pipeline
def productService(stockCode: str) -> ProductServiceResult | None:
    """주요 제품 및 서비스 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> productService(...)

    Returns:
        <TODO: return desc> (ProductServiceResult | None)

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
            if "주요 제품" in title or "주요 서비스" in title:
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = detectUnit(content)
                products = parseProductService(content)

                if not products:
                    if "없습니다" in content[:500] or len(content) < 200:
                        return ProductServiceResult(
                            corpName=corpName,
                            nYears=1,
                            unit=unit,
                            noData=True,
                        )
                    continue

                productDf = pl.DataFrame(
                    {
                        "label": [p["label"] for p in products],
                        "amount": [p.get("amount") for p in products],
                        "ratio": [p.get("ratio") for p in products],
                    },
                    schema={
                        "label": pl.Utf8,
                        "amount": pl.Int64,
                        "ratio": pl.Float64,
                    },
                )

                return ProductServiceResult(
                    corpName=corpName,
                    nYears=1,
                    unit=unit,
                    products=products,
                    noData=False,
                    productDf=productDf,
                )

    return None
