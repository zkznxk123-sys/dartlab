"""타법인출자 현황 파이프라인.

P2 통합: 기존 investmentInOther/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class InvestmentInOtherResult:
    """타법인출자 현황 분석 결과."""

    corpName: str | None = None
    nYears: int = 0
    investments: list[dict] = field(default_factory=list)
    noData: bool = False
    investmentDf: pl.DataFrame | None = None


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
        list[str] — 결과.
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
        bool — 결과.
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
        int | None — 결과.
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


def parseInvestments(content: str) -> tuple[list[dict], list[str]]:
    """타법인출자 현황 파싱.

    Returns:
        (rows, headers) — rows: [{"name": str, "values": [int]}], headers: 숫자 컬럼 헤더

    Raises:
        없음.

    Example:
        >>> parseInvestments(...)

    Args:
        content: str.
    """
    lines = content.split("\n")
    results: list[dict] = []
    headerFound = False
    numericHeaders: list[str] = []

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
        if any("법인명" in c or "회사명" in c or "종목명" in c for c in cells) and any(
            "지분" in c or "장부" in c or "취득" in c or "기초" in c or "기말" in c for c in cells
        ):
            headerFound = True
            # 헤더에서 숫자 컬럼명 추출 (법인명 이후의 셀들)
            nameIdx = 0
            for i, c in enumerate(cells):
                if "법인명" in c or "회사명" in c or "종목명" in c:
                    nameIdx = i
                    break
            numericHeaders = [c.strip().replace(" ", "") for c in cells[nameIdx + 1 :] if c.strip()]
            continue

        if not headerFound:
            continue

        # 합계 행 스킵
        if any(c.strip() in ("합계", "합 계", "소계", "소 계", "총계") for c in cells):
            continue

        # 데이터 행: 법인명 + 숫자
        name = ""
        nums = []
        for c in cells:
            val = parseAmount(c)
            if val is not None:
                nums.append(val)
            elif c.strip() and len(c.strip()) >= 2 and c.strip() not in ("-", "\u2212", "\u2013"):
                if not name:
                    name = c.strip()

        if not name or not nums:
            continue

        results.append({"name": name, "values": nums})

    return results, numericHeaders


# pipeline
def _buildInvestmentDf(rows: list[dict], headers: list[str] | None = None) -> pl.DataFrame | None:
    if not rows:
        return None
    maxVals = max(len(r["values"]) for r in rows)
    data: dict[str, list] = {"name": [r["name"] for r in rows]}
    for i in range(maxVals):
        colName = headers[i] if headers and i < len(headers) else f"v{i + 1}"
        if colName in data:
            colName = f"{colName}_{i + 1}"
        data[colName] = [r["values"][i] if i < len(r["values"]) else None for r in rows]
    return pl.DataFrame(data)


def investmentInOther(stockCode: str) -> InvestmentInOtherResult | None:
    """타법인출자 현황 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> investmentInOther(...)

    Returns:
        InvestmentInOtherResult | None — 결과.
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
            if "타법인" in title and ("출자" in title or "투자" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                investments, headers = parseInvestments(content)
                if investments:
                    return InvestmentInOtherResult(
                        corpName=corpName,
                        nYears=1,
                        investments=investments,
                        investmentDf=_buildInvestmentDf(investments, headers),
                    )

                if "해당사항" in content[:500] or "없습니다" in content[:500]:
                    return InvestmentInOtherResult(corpName=corpName, nYears=1, noData=True)
    return None
