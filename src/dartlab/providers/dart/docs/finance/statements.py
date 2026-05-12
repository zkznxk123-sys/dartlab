"""재무제표 추출 파이프라인. 연결 우선, 별도 fallback.

P2 통합: 기존 statements/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import PERIOD_KINDS, extractCorpName, loadData
from dartlab.core.reportSelector import parsePeriodKey, selectReport
from dartlab.core.tableParser import extractAccounts

if TYPE_CHECKING:
    import polars as pl


# types
@dataclass
class StatementsResult:
    """StatementsResult — TODO 한국어 클래스 설명."""

    corpName: str | None
    period: str  # "y" | "q" | "h"
    scope: str = "consolidated"  # "consolidated" | "separate"
    nYears: int = 0
    BS: pl.DataFrame | None = None  # 재무상태표
    IS: pl.DataFrame | None = None  # 손익계산서
    CF: pl.DataFrame | None = None  # 현금흐름표


# parser
_STATEMENT_PATTERNS = {
    "BS": r"재무상태표",
    "CI": r"포괄손익",
    # PNL 은 '포괄' 이 앞에 없는 '손익계산서' 만 매칭. 순서도 CI 뒤에 두어 이중 방어.
    "PNL": r"(?<!포괄)손익계산서",
    "SCE": r"자본변동표",
    "CF": r"현금흐름표",
}


def extractContent(
    report: pl.DataFrame,
    scope: str | None = None,
) -> tuple[str | None, str]:
    """보고서에서 재무제표 섹션 추출.

    Args:
        report: 보고서 DataFrame
        scope: 지정 시 해당 scope만 추출
            None — 연결 우선, 별도 fallback (기본)
            "consolidated" — 연결만
            "separate" — 별도만

    Returns:
        (content, scope) — scope은 "consolidated" | "separate"
        추출 불가 시 (None, "none")

    Raises:
        없음.

    Example:
        >>> extractContent(...)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    if scope != "separate":
        cons = report.filter(
            pl.col("section_title").str.contains("연결재무제표") & ~pl.col("section_title").str.contains("주석")
        )
        if cons.height > 0:
            content = cons["section_content"][0]
            # "연결대상이 없어 연결재무제표를 작성하지 않습니다" 처리
            hasNoSub = "연결대상" in content and ("없어" in content or "없으므로" in content)
            if not hasNoSub:
                if scope == "consolidated":
                    return content, "consolidated"
                return content, "consolidated"

        if scope == "consolidated":
            return None, "none"

    # 별도/개별 재무제표
    sep = report.filter(
        pl.col("section_title").str.contains("재무제표")
        & ~pl.col("section_title").str.contains("연결")
        & ~pl.col("section_title").str.contains("주석")
    )
    if sep.height > 0:
        return sep["section_content"][0], "separate"

    return None, "none"


def extractConsolidatedContent(report: pl.DataFrame) -> str | None:
    """보고서에서 연결재무제표 섹션 내용을 추출. (하위 호환)

    Args:
        report: 인자.

    Raises:
        없음.

    Example:
        >>> extractConsolidatedContent(...)

    Returns:
        <TODO: return desc> (str | None)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    content, scope = extractContent(report)
    return content


def splitStatements(content: str) -> dict[str, str]:
    """재무제표 전체 내용을 개별 제표별 텍스트로 분리.

    Returns:
        {"BS": "...", "PNL": "...", "CI": "...", "SCE": "...", "CF": "..."}

    Raises:
        없음.

    Example:
        >>> splitStatements(...)

    Args:
        content: <TODO: param desc> (str)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    lines = content.split("\n")

    # 헤더 위치 찾기
    # 2024+: "2-1. 연결 재무상태표" (독립 행)
    # ~2023: "| 연결 재무상태표 |" (테이블 행, 셀 1개)
    # 일부 기업: "연 결 재 무 상 태 표" (공백 삽입)
    headers: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or len(s) >= 80:
            continue

        # 테이블 행인 경우: 셀이 1개이고 키워드 포함 시에만 헤더로 인식
        if s.startswith("|"):
            cells = [c.strip() for c in s.split("|") if c.strip()]
            if len(cells) != 1:
                continue
            s = cells[0]

        # 공백 제거 후 패턴 매칭 ("재 무 상 태 표" → "재무상태표")
        sNoSpace = re.sub(r"\s+", "", s)
        for key, pattern in _STATEMENT_PATTERNS.items():
            if re.search(pattern, sNoSpace):
                headers.append((i, key))
                break

    # 중복 키 처리: 뒤에 나온 게 우선 (포괄손익 vs 손익계산서 구분)
    seen: dict[str, int] = {}
    uniqueHeaders: list[tuple[int, str]] = []
    for idx, key in headers:
        if key in seen:
            uniqueHeaders[seen[key]] = (idx, key)
        else:
            seen[key] = len(uniqueHeaders)
            uniqueHeaders.append((idx, key))

    result: dict[str, str] = {}
    for j, (startIdx, key) in enumerate(uniqueHeaders):
        if j + 1 < len(uniqueHeaders):
            endIdx = uniqueHeaders[j + 1][0]
        else:
            endIdx = len(lines)
        result[key] = "\n".join(lines[startIdx:endIdx])

    return result


# pipeline
def statements(
    stockCode: str,
    ifrsOnly: bool = True,
    period: str = "y",
    scope: str | None = None,
) -> StatementsResult | None:
    """재무제표에서 BS, IS, CF 시계열 DataFrame 추출.

    Args:
        stockCode: 종목코드 (6자리)
        ifrsOnly: True면 K-IFRS 이후(2011~)만
        period: "y" | "q" | "h"
        scope: 재무제표 종류 지정
            None — 연결 우선, 별도 fallback (기본)
            "consolidated" — 연결만
            "separate" — 별도만

    Returns:
        StatementsResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> statements(...)

    SeeAlso:
        - <TODO: 관련 함수/엔진>

    Requires:
        - dartlab
        - polars
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    kinds = PERIOD_KINDS.get(period, PERIOD_KINDS["y"])
    years = sorted(df["year"].unique().to_list(), reverse=True)

    # 기간별 각 제표 데이터 수집
    bsData: dict[str, tuple[dict, list]] = {}
    isData: dict[str, tuple[dict, list]] = {}
    cfData: dict[str, tuple[dict, list]] = {}
    scopes: set[str] = set()

    for year in years:
        for kind in kinds:
            report = selectReport(df, year, reportKind=kind)
            if report is None:
                continue

            content, contentScope = extractContent(report, scope=scope)
            if content is None:
                continue

            scopes.add(contentScope)
            parts = splitStatements(content)

            if period == "y":
                key = year
            else:
                reportType = report["report_type"][0]
                key = parsePeriodKey(reportType)
                if key is None:
                    continue

            if ifrsOnly and int(key[:4]) < 2011:
                continue

            for stKey, stContent, target in [
                ("BS", parts.get("BS"), bsData),
                ("IS", parts.get("PNL"), isData),
                ("CF", parts.get("CF"), cfData),
            ]:
                if stContent is None:
                    continue
                accounts, order = extractAccounts(stContent)
                if accounts:
                    target[key] = (accounts, order)

    if not bsData and not isData and not cfData:
        return None

    allKeys = sorted(set(bsData) | set(isData) | set(cfData), reverse=True)

    resultScope = "consolidated" if "consolidated" in scopes else "separate"

    return StatementsResult(
        corpName=corpName,
        period=period,
        scope=resultScope,
        nYears=len(allKeys),
        BS=_buildDf(allKeys, bsData),
        IS=_buildDf(allKeys, isData),
        CF=_buildDf(allKeys, cfData),
    )


def _buildDf(
    sortedKeys: list[str],
    data: dict[str, tuple[dict, list]],
) -> pl.DataFrame:
    """항목 직접 매칭 방식으로 DataFrame 생성."""
    nameData: dict[str, dict[str, float | None]] = {}
    accountOrder: list[str] = []

    for key in sortedKeys:
        if key not in data:
            continue
        accounts, order = data[key]
        for name in order:
            if name not in nameData:
                nameData[name] = {}
                accountOrder.append(name)
            amts = accounts[name]
            nameData[name][key] = amts[0] if amts else None

    rows = []
    for name in accountOrder:
        row: dict[str, object] = {"항목": name}
        for key in sortedKeys:
            row[key] = nameData[name].get(key)
        rows.append(row)

    if not rows:
        return pl.DataFrame()

    schema = {"항목": pl.Utf8}
    for key in sortedKeys:
        schema[key] = pl.Float64
    return pl.DataFrame(rows, schema=schema)
