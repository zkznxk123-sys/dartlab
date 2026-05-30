"""임원 현황 데이터 추출 파이프라인."""

import re

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData, yearsDesc
from dartlab.providers._common.reportSelector import selectReport
from dartlab.providers.dart.docs.finance.executive.parser import (
    aggregateExecutives,
    classifyBlock,
    extractTableBlocks,
    parseExecutiveBlock,
    parseUnregisteredPayBlock,
)
from dartlab.providers.dart.docs.finance.executive.types import ExecutiveResult

EXECUTIVE_SECTION_PATTERNS = [
    r"임원.*직원.*현황",
    r"임원.*현황",
]


def executive(stockCode: str) -> ExecutiveResult | None:
    """사업보고서에서 임원 현황 시계열 추출.

    등기임원 집계(사내/사외/기타, 상근/비상근, 성별) + 미등기임원 보수 시계열.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        ExecutiveResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> executive(...)
    """
    df = loadData(stockCode)
    if df is None or df.is_empty() or "year" not in df.columns:
        return None
    corpName = extractCorpName(df)
    years = yearsDesc(df)

    execRows: list[dict] = []
    individualRows: list[dict] = []
    payRows: list[dict] = []

    for year in years:
        content = _findExecutiveSection(df, year)
        if content is None:
            continue

        blocks = extractTableBlocks(content)

        # 등기임원
        for block in blocks:
            if classifyBlock(block) == "executive":
                executives = parseExecutiveBlock(block)
                if executives:
                    stats = aggregateExecutives(executives)
                    stats["year"] = int(year)
                    execRows.append(stats)
                    for e in executives:
                        individualRows.append({**e, "year": int(year)})
                break

        # 미등기임원 보수
        for block in blocks:
            if classifyBlock(block) == "unregisteredPay":
                pay = parseUnregisteredPayBlock(block)
                if pay:
                    pay["year"] = int(year)
                    payRows.append(pay)
                break

    if not execRows and not payRows:
        return None

    execRows = _dedup(execRows)
    payRows = _dedup(payRows)
    individualRows = _dedupIndividual(individualRows)

    executiveDf = _buildExecutiveDf(execRows) if execRows else None
    individualDf = _buildIndividualDf(individualRows) if individualRows else None
    unregPayDf = _buildUnregPayDf(payRows) if payRows else None

    nYears = max(len(execRows), len(payRows))

    return ExecutiveResult(
        corpName=corpName,
        nYears=nYears,
        executiveDf=executiveDf,
        individualDf=individualDf,
        unregPayDf=unregPayDf,
    )


def _findExecutiveSection(df: pl.DataFrame, year: str) -> str | None:
    """임원 현황 섹션의 content 반환. 소분류 우선."""
    report = selectReport(df, year, reportKind="annual")
    if report is None:
        return None

    candidates = []
    for row in report.iter_rows(named=True):
        title = row.get("section_title", "") or ""
        if any(re.search(p, title) for p in EXECUTIVE_SECTION_PATTERNS):
            isSub = not title.startswith(("V", "VI", "VII", "VIII", "IX"))
            candidates.append(
                {
                    "content": row.get("section_content", "") or "",
                    "isSub": isSub,
                }
            )

    if not candidates:
        return None

    sub = [c for c in candidates if c["isSub"]]
    if sub:
        return sub[0]["content"]
    return candidates[0]["content"]


def _dedup(rows: list[dict]) -> list[dict]:
    """연도별 중복 제거 (최신 우선)."""
    seen: set[int] = set()
    result = []
    for r in rows:
        if r["year"] not in seen:
            seen.add(r["year"])
            result.append(r)
    return result


def _buildExecutiveDf(rows: list[dict]) -> pl.DataFrame:
    data = []
    for r in sorted(rows, key=lambda x: x["year"]):
        data.append(
            {
                "year": r["year"],
                "totalRegistered": r["totalRegistered"],
                "insideDirectors": r["insideDirectors"],
                "outsideDirectors": r["outsideDirectors"],
                "otherNonexec": r["otherNonexec"],
                "fullTimeCount": r["fullTimeCount"],
                "partTimeCount": r["partTimeCount"],
                "maleCount": r["maleCount"],
                "femaleCount": r["femaleCount"],
                "ceoCount": r.get("ceoCount", 0),
            }
        )
    return pl.DataFrame(data)


def _dedupIndividual(rows: list[dict]) -> list[dict]:
    """(year, name) 중복 제거 — 같은 연도에 블록 두 번 파싱된 경우 대비."""
    seen: set[tuple[int, str]] = set()
    result = []
    for r in rows:
        key = (r["year"], r.get("name", ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(r)
    return result


def _buildIndividualDf(rows: list[dict]) -> pl.DataFrame:
    schema = {
        "year": pl.Int64,
        "name": pl.Utf8,
        "gender": pl.Utf8,
        "position": pl.Utf8,
        "registrationType": pl.Utf8,
        "fullTime": pl.Utf8,
        "responsibility": pl.Utf8,
        "isCeo": pl.Boolean,
    }
    data = []
    for r in sorted(rows, key=lambda x: (x["year"], x.get("name", ""))):
        data.append(
            {
                "year": r["year"],
                "name": r.get("name", ""),
                "gender": r.get("gender", ""),
                "position": r.get("position", ""),
                "registrationType": r.get("registrationType", ""),
                "fullTime": r.get("fullTime", ""),
                "responsibility": r.get("responsibility", ""),
                "isCeo": bool(r.get("isCeo", False)),
            }
        )
    return pl.DataFrame(data, schema=schema)


def _buildUnregPayDf(rows: list[dict]) -> pl.DataFrame:
    data = []
    for r in sorted(rows, key=lambda x: x["year"]):
        data.append(
            {
                "year": r["year"],
                "headcount": r["headcount"],
                "totalSalary": r["totalSalary"],
                "avgSalary": r["avgSalary"],
            }
        )
    schema = {
        "year": pl.Int64,
        "headcount": pl.Int64,
        "totalSalary": pl.Float64,
        "avgSalary": pl.Float64,
    }
    return pl.DataFrame(data, schema=schema)
