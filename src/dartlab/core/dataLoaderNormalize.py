"""Loaded parquet normalization helpers for ``core.dataLoader``."""

from __future__ import annotations

import re

import polars as pl

CATEGORICAL_COLS = frozenset(
    {
        "source",
        "account_id",
        "blockType",
        "form_type",
    }
)

DOWNCAST_INT_COLS = frozenset(
    {
        "year",
        "section_order",
        "bsns_year",
    }
)


def optimizeMemory(df: pl.DataFrame) -> pl.DataFrame:
    """Categorical 전환 + Int 다운캐스트로 메모리 절감."""
    exprs: list[pl.Expr] = []
    schema = df.schema
    for col, dtype in schema.items():
        if col in CATEGORICAL_COLS and dtype == pl.Utf8:
            exprs.append(pl.col(col).cast(pl.Categorical))
        elif col in DOWNCAST_INT_COLS and dtype == pl.Int64:
            exprs.append(pl.col(col).cast(pl.Int32))
    if exprs:
        return df.with_columns(exprs)
    return df


def normalizeLoadedFrame(df: pl.DataFrame, category: str) -> pl.DataFrame:
    """loadData 반환 직전 category별 표준 컬럼과 메모리 타입을 정리한다."""
    if "__index_level_0__" in df.columns:
        df = df.drop("__index_level_0__")
    if category == "edgarDocs":
        df = normalizeEdgarDocs(df)
    return optimizeMemory(df)


def normalizeEdgarDocs(df: pl.DataFrame) -> pl.DataFrame:
    """EDGAR docs parquet에 공통 docs 컬럼 alias와 period_key를 부여한다."""
    cols = set(df.columns)
    exprs: list[pl.Expr] = []

    if "report_type" not in cols and "form_type" in cols:
        exprs.append(
            pl.struct([col for col in ("form_type", "period_end", "year") if col in cols])
            .map_elements(edgarReportTypeFromRow, return_dtype=pl.Utf8)
            .alias("report_type")
        )

    if "source" not in cols:
        exprs.append(pl.lit("edgar").alias("source"))
    if "entity_id" not in cols and "ticker" in cols:
        exprs.append(pl.col("ticker").alias("entity_id"))
    if "doc_id" not in cols and "accession_no" in cols:
        exprs.append(pl.col("accession_no").alias("doc_id"))
    if "doc_date" not in cols and "filing_date" in cols:
        exprs.append(pl.col("filing_date").alias("doc_date"))
    if "doc_url" not in cols and "filing_url" in cols:
        exprs.append(pl.col("filing_url").alias("doc_url"))

    result = df.with_columns(exprs) if exprs else df
    return applyEdgarPeriodKeys(result)


def edgarReportTypeFromRow(row: dict) -> str | None:
    """EDGAR filing row에서 사람이 읽는 report_type을 만든다."""
    formType = row.get("form_type")
    periodEnd = row.get("period_end")
    year = row.get("year")
    if not formType:
        return None
    if not periodEnd:
        if formType in ("10-K", "20-F", "40-F") and year:
            return f"{formType} ({year}.12)"
        return str(formType)

    match = re.match(r"(\d{4})-(\d{2})", str(periodEnd))
    if not match:
        return str(formType)
    year, month = match.groups()
    return f"{formType} ({year}.{month})"


def applyEdgarPeriodKeys(df: pl.DataFrame) -> pl.DataFrame:
    """EDGAR accession_no 단위 period_key를 유추해 docs frame에 붙인다."""
    if "accession_no" not in df.columns or "form_type" not in df.columns:
        return df

    cols = [col for col in ("accession_no", "form_type", "filing_date", "period_end", "year") if col in df.columns]
    filingDf = df.select(cols).unique(subset=["accession_no"]).sort(["filing_date", "accession_no"])
    filings = filingDf.to_dicts()
    periodMap = inferEdgarPeriodKeyMap(filings)
    if not periodMap:
        return df

    return df.with_columns(
        pl.col("accession_no")
        .map_elements(lambda accession: periodMap.get(str(accession)), return_dtype=pl.Utf8)
        .alias("period_key")
    )


def inferEdgarPeriodKeyMap(filings: list[dict]) -> dict[str, str | None]:
    """정렬된 EDGAR filing 목록에서 accession_no→period_key 맵을 유추한다."""
    annualForms = {"10-K", "20-F", "40-F"}
    enriched = []
    for filing in filings:
        accession = str(filing.get("accession_no") or "")
        formType = str(filing.get("form_type") or "")
        filingDate = str(filing.get("filing_date") or "")
        periodEnd = filing.get("period_end")
        periodEndStr = str(periodEnd) if periodEnd else ""
        sortKey = periodEndStr or filingDate
        enriched.append(
            {
                "accession_no": accession,
                "form_type": formType,
                "filing_date": filingDate,
                "period_end": periodEndStr,
                "year": str(filing.get("year") or ""),
                "sort_key": sortKey,
            }
        )

    enriched.sort(key=lambda row: (row["sort_key"], row["filing_date"], row["accession_no"]))
    periodMap: dict[str, str | None] = {}

    annualIdx = [i for i, row in enumerate(enriched) if row["form_type"] in annualForms and row["period_end"]]

    for idx in annualIdx:
        annual = enriched[idx]
        periodMap[annual["accession_no"]] = annual["period_end"][:4]

    for pos in range(1, len(annualIdx)):
        prevAnnual = annualIdx[pos - 1]
        curAnnual = annualIdx[pos]
        fy = enriched[curAnnual]["period_end"][:4]
        qRows = [row for row in enriched[prevAnnual + 1 : curAnnual] if row["form_type"] == "10-Q"]
        for qNum, row in enumerate(qRows[:3], start=1):
            periodMap[row["accession_no"]] = f"{fy}Q{qNum}"

    if annualIdx:
        lastAnnual = annualIdx[-1]
        lastFy = int(enriched[lastAnnual]["period_end"][:4])
        qRows = [row for row in enriched[lastAnnual + 1 :] if row["form_type"] == "10-Q"]
        for qNum, row in enumerate(qRows[:3], start=1):
            periodMap[row["accession_no"]] = f"{lastFy + 1}Q{qNum}"

    if not annualIdx:
        for row in enriched:
            if row["form_type"] in annualForms and row["year"]:
                periodMap[row["accession_no"]] = row["year"]

    return periodMap


__all__ = [
    "applyEdgarPeriodKeys",
    "edgarReportTypeFromRow",
    "inferEdgarPeriodKeyMap",
    "normalizeEdgarDocs",
    "normalizeLoadedFrame",
    "optimizeMemory",
]
