"""위험관리 및 파생거래 파이프라인.

P2 통합: 기존 riskDerivative/{parser,pipeline,types}.py 단일 모듈로 흡수.
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
class RiskDerivativeResult:
    """위험관리 및 파생거래 분석 결과.

    Attributes:
        corpName: 기업명
        nYears: 시계열 연도 수
        unit: 단위 (백만원 등)
        fxSensitivity: 환율 민감도 [{currency, upImpact, downImpact}, ...]
        derivatives: 파생상품 계약 [{label, values}, ...]
        noData: 해당사항 없음 여부
        textOnly: 서술형만 존재 (테이블 없음)
        fxDf: 환율 민감도 DataFrame (currency | upImpact | downImpact)
        derivativeDf: 파생상품 DataFrame (label | v1 | v2 | ...)
    """

    corpName: str | None = None
    nYears: int = 0
    unit: str = "백만원"
    fxSensitivity: list[dict] = field(default_factory=list)
    derivatives: list[dict] = field(default_factory=list)
    noData: bool = False
    textOnly: bool = False
    fxDf: pl.DataFrame | None = None
    derivativeDf: pl.DataFrame | None = None


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
    """
    m = re.search(r"단위\s*[:\s]*\s*(백만원|억원|천원|원)", content[:500])
    if m:
        return m.group(1)
    return "백만원"


def parseFxSensitivity(content: str) -> list[dict]:
    """환율 민감도 테이블 파싱.

    Args:
        content: 인자.

    Raises:
        없음.

    Example:
        >>> parseFxSensitivity(...)

    Returns:
        <TODO: return desc> (list[dict])
    """
    lines = content.split("\n")
    results: list[dict] = []

    inSection = False
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if re.search(r"환율.*변동|환율.*민감도|외화.*민감도", stripped):
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 2:
            continue

        if any("단위" in c for c in cells):
            continue
        if any("※" in c for c in cells):
            break

        if any("상승" in c or "하락" in c for c in cells):
            headerFound = True
            continue

        if not headerFound:
            continue

        currency = cells[0].strip()
        if not currency or currency in ("-", "−", "–") or len(currency) > 10:
            continue

        nums = [parseAmount(c) for c in cells[1:]]
        validNums = [n for n in nums if n is not None]
        if not validNums:
            continue

        entry = {"currency": currency}
        if len(validNums) >= 1:
            entry["upImpact"] = validNums[0]
        if len(validNums) >= 2:
            entry["downImpact"] = validNums[1]
        results.append(entry)

    return results


def _extractValueHeaders(headerCols: list[str]) -> list[str]:
    """헤더 행에서 라벨 키워드를 제외한 값 컬럼 헤더 추출."""
    labelKeywords = {"종류", "구분", "거래상대방", "거래대상", "파생상품"}
    valueHeaders = []
    for c in headerCols:
        s = c.strip()
        if not s or s in labelKeywords:
            continue
        valueHeaders.append(s)
    return valueHeaders


def parseDerivativeContracts(content: str) -> tuple[list[dict], list[str]]:
    """파생상품 계약 현황 파싱.

    Returns:
        (rows, valueHeaders) 튜플.

    Raises:
        없음.

    Example:
        >>> parseDerivativeContracts(...)

    Args:
        content: <TODO: param desc> (str)
    """
    lines = content.split("\n")
    results: list[dict] = []

    inSection = False
    headerCols: list[str] = []
    headerFound = False

    for line in lines:
        stripped = line.strip()

        if not inSection:
            if re.search(r"파생상품.*계약|파생상품.*현황|파생상품.*거래", stripped):
                inSection = True
            continue

        if "|" not in stripped or isSeparatorRow(stripped):
            if headerFound and results:
                break
            continue

        cells = splitCells(stripped)
        if len(cells) < 3:
            continue

        if any("단위" in c or "기준일" in c for c in cells):
            continue

        if any("종류" in c or "구분" in c for c in cells) and any("금액" in c or "손익" in c for c in cells):
            headerCols = cells
            headerFound = True
            continue

        if not headerFound:
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

        results.append(
            {
                "label": " > ".join(label_parts),
                "values": values,
            }
        )

    valueHeaders = _extractValueHeaders(headerCols) if headerCols else []
    return results, valueHeaders


# pipeline
def _buildDerivativeDf(
    rows: list[dict],
    headers: list[str] | None = None,
) -> pl.DataFrame | None:
    """파생상품 행 목록을 DataFrame으로 변환."""
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


def riskDerivative(stockCode: str) -> RiskDerivativeResult | None:
    """위험관리 및 파생거래 분석.

    Args:
        stockCode: 인자.

    Raises:
        없음.

    Example:
        >>> riskDerivative(...)

    Returns:
        <TODO: return desc> (RiskDerivativeResult | None)
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
            if ("위험관리" in title and "파생" in title) or ("파생" in title and "거래" in title):
                content = row.get("section_content", "") or ""
                if len(content) < 50:
                    continue

                unit = detectUnit(content)
                fxSensitivity = parseFxSensitivity(content)
                derivatives, derivHeaders = parseDerivativeContracts(content)

                if not fxSensitivity and not derivatives:
                    if "없습니다" in content[:500] or "해당사항" in content[:500] or len(content) < 300:
                        return RiskDerivativeResult(
                            corpName=corpName,
                            nYears=1,
                            unit=unit,
                            noData=True,
                        )
                    hasRisk = any(k in content for k in ("환율", "이자율", "시장위험", "신용위험"))
                    if hasRisk:
                        return RiskDerivativeResult(
                            corpName=corpName,
                            nYears=1,
                            unit=unit,
                            textOnly=True,
                        )
                    continue

                fxDf = None
                if fxSensitivity:
                    fxDf = pl.DataFrame(
                        {
                            "currency": [f["currency"] for f in fxSensitivity],
                            "upImpact": [f.get("upImpact") for f in fxSensitivity],
                            "downImpact": [f.get("downImpact") for f in fxSensitivity],
                        },
                        schema={
                            "currency": pl.Utf8,
                            "upImpact": pl.Int64,
                            "downImpact": pl.Int64,
                        },
                    )

                return RiskDerivativeResult(
                    corpName=corpName,
                    nYears=1,
                    unit=unit,
                    fxSensitivity=fxSensitivity,
                    derivatives=derivatives,
                    fxDf=fxDf,
                    derivativeDf=_buildDerivativeDf(derivatives, derivHeaders),
                )

    return None
