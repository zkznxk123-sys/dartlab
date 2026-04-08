"""전 종목 발행주식수 일괄 빌더 — docs glob scan + parser 재사용.

`data/dart/docs/*.parquet` 2900+ 종목 × 1만+ 보고서를 polars LazyFrame 으로
한 번에 스캔해 `4. 주식의 총수 등` 섹션만 추출하고, 기존 검증된 parser 를
재사용해 분기별 보통주/우선주 발행주식수를 만든다.

산출물: `data/dart/scan/sharesOutstanding.parquet`

스키마:
    stock_code, corp_name, year, rcept_date, rcept_no, report_type,
    authorizedShares, issuedShares, retiredShares,
    outstandingShares, treasuryShares, floatingShares, treasuryRatio,
    preferredIssued, preferredOutstanding, preferredTreasury, preferredFloating,
    source

source 는 항상 "dart_docs". marketCap 합성 시 as-of join 키는
`(stock_code, rcept_date)`.
"""

from __future__ import annotations

import logging
from pathlib import Path

import polars as pl

from dartlab.providers.dart.docs.finance.shareCapital.parser import parseShareCapitalTable

log = logging.getLogger(__name__)

_SECTION_TITLE = "4. 주식의 총수 등"

_OUTPUT_COLUMNS = [
    "stock_code",
    "corp_name",
    "year",
    "rcept_date",
    "rcept_no",
    "report_type",
    "authorizedShares",
    "issuedShares",
    "retiredShares",
    "outstandingShares",
    "treasuryShares",
    "floatingShares",
    "treasuryRatio",
    "preferredIssued",
    "preferredOutstanding",
    "preferredTreasury",
    "preferredFloating",
    "source",
]


def buildSharesOutstandingScan(
    *,
    docsDir: str | Path | None = None,
    outputPath: str | Path | None = None,
    write: bool = True,
) -> pl.DataFrame:
    """전 종목 docs glob → 발행주식수 DataFrame.

    Args:
        docsDir: docs parquet 디렉토리. None이면 `data/dart/docs/`.
        outputPath: 출력 parquet 경로. None이면 `data/dart/scan/sharesOutstanding.parquet`.
        write: True면 parquet 저장. False면 DataFrame 만 반환.

    Returns:
        발행주식수 DataFrame (rcept_date desc 정렬).
    """
    from dartlab.core.dataLoader import _dataDir

    docsRoot = Path(docsDir) if docsDir else Path(_dataDir("docs"))
    if not docsRoot.exists():
        raise FileNotFoundError(f"docs 디렉토리 없음: {docsRoot}")

    parquetFiles = sorted(docsRoot.glob("*.parquet"))
    if not parquetFiles:
        raise FileNotFoundError(f"docs parquet 없음: {docsRoot}")

    log.info("[shares] scanning %d docs parquets (per-file)", len(parquetFiles))

    keepCols = [
        "stock_code",
        "corp_name",
        "year",
        "rcept_date",
        "rcept_no",
        "report_type",
        "section_content",
    ]

    records: list[dict] = []
    skipped = 0
    failedFiles = 0
    sectionRows = 0
    for idx, pf in enumerate(parquetFiles):
        try:
            sub = pl.scan_parquet(str(pf)).filter(pl.col("section_title") == _SECTION_TITLE).select(keepCols).collect()
        except (pl.exceptions.PolarsError, OSError):
            failedFiles += 1
            continue
        if sub.is_empty():
            continue
        sectionRows += sub.height
        for row in sub.iter_rows(named=True):
            parsed = parseShareCapitalTable(row["section_content"], includePreferred=True)
            if parsed is None:
                skipped += 1
                continue
            records.append(
                {
                    "stock_code": row["stock_code"],
                    "corp_name": row["corp_name"],
                    "year": row["year"],
                    "rcept_date": row["rcept_date"],
                    "rcept_no": row["rcept_no"],
                    "report_type": row["report_type"],
                    "authorizedShares": parsed.get("authorizedShares"),
                    "issuedShares": parsed.get("issuedShares"),
                    "retiredShares": parsed.get("retiredShares"),
                    "outstandingShares": parsed.get("outstandingShares"),
                    "treasuryShares": parsed.get("treasuryShares"),
                    "floatingShares": parsed.get("floatingShares"),
                    "treasuryRatio": parsed.get("treasuryRatio"),
                    "preferredIssued": parsed.get("preferredIssued"),
                    "preferredOutstanding": parsed.get("preferredOutstanding"),
                    "preferredTreasury": parsed.get("preferredTreasury"),
                    "preferredFloating": parsed.get("preferredFloating"),
                    "source": "dart_docs",
                }
            )
        if (idx + 1) % 500 == 0:
            log.info("[shares] progress %d/%d (records=%d)", idx + 1, len(parquetFiles), len(records))

    log.info(
        "[shares] section_rows=%d parsed=%d skipped=%d failedFiles=%d",
        sectionRows,
        len(records),
        skipped,
        failedFiles,
    )

    if not records:
        raise RuntimeError("발행주식수 추출 결과가 비어있음")

    out = pl.DataFrame(records, schema_overrides={"rcept_date": pl.Utf8}).select(_OUTPUT_COLUMNS)
    out = out.sort(["stock_code", "rcept_date"], descending=[False, True])

    coverage = out["stock_code"].n_unique()
    log.info("[shares] %d unique stocks covered", coverage)

    if write:
        if outputPath is None:
            scanDir = Path(_dataDir("scan"))
            scanDir.mkdir(parents=True, exist_ok=True)
            outputPath = scanDir / "sharesOutstanding.parquet"
        outputPath = Path(outputPath)
        outputPath.parent.mkdir(parents=True, exist_ok=True)
        out.write_parquet(outputPath)
        log.info("[shares] wrote %s (%d rows)", outputPath, out.height)

    return out
