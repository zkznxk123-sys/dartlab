"""주식의 총수 데이터 추출 파이프라인.

P2 통합: 기존 shareCapital/{parser,pipeline,types}.py 단일 모듈로 흡수.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from dartlab.core.dataLoader import extractCorpName, loadData
from dartlab.providers._common.reportSelector import extractReportYear, selectReport
from dartlab.providers._common.tableParser import parseAmount

if TYPE_CHECKING:
    pass


# types
@dataclass
class ShareCapitalResult:
    """주식의 총수 분석 결과."""

    corpName: str | None
    nYears: int
    authorizedShares: float | None = None
    issuedShares: float | None = None
    retiredShares: float | None = None
    outstandingShares: float | None = None
    treasuryShares: float | None = None
    floatingShares: float | None = None
    treasuryRatio: float | None = None
    timeSeries: pl.DataFrame | None = None


# parser
FIELD_MAP = {
    "발행할 주식의 총수": "authorizedShares",
    "현재까지 발행한 주식의 총수": "issuedShares",
    "현재까지 감소한 주식의 총수": "retiredShares",
    "발행주식의 총수": "outstandingShares",
    "자기주식수": "treasuryShares",
    "유통주식수": "floatingShares",
    "자기주식 보유비율": "treasuryRatio",
}


def parseShareCapitalTable(content: str, *, includePreferred: bool = False) -> dict | None:
    """주식의 총수 테이블 파싱.

    Ⅰ~Ⅶ 번호 체계에서 발행주식/자기주식/유통주식 추출.
    표는 (label, [빈셀], 보통주, 우선주, 합계, 비고) 순서.

    Args:
        content: section_content 마크다운 텍스트
        includePreferred: True면 우선주 필드도 추출 (preferred* 키 추가)

    Returns:
        dict with keys: authorizedShares, issuedShares, retiredShares,
            outstandingShares, treasuryShares, floatingShares, treasuryRatio
        includePreferred=True일 때 추가: preferredOutstanding, preferredTreasury,
            preferredFloating, preferredIssued
        또는 발행주식 총수를 추출할 수 없으면 None

    Raises:
        없음.

    Example:
        >>> parseShareCapitalTable(...)
    """
    lines = content.split("\n")
    result: dict = {}

    # 우선주는 outstandingShares/treasuryShares/floatingShares/issuedShares만 캡쳐
    _PREF_FIELDS = {
        "outstandingShares": "preferredOutstanding",
        "treasuryShares": "preferredTreasury",
        "floatingShares": "preferredFloating",
        "issuedShares": "preferredIssued",
    }

    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue

        cells = [c.strip() for c in s.split("|")]
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if len(cells) < 3:
            continue

        txt = " ".join(cells[:2])
        for keyword, field in FIELD_MAP.items():
            if keyword in txt:
                # 숫자 셀들을 등장 순서대로 수집 — [공통, 우선, 합계] 또는 [공통]
                nums: list[float] = []
                for ci in range(1, len(cells)):
                    v = parseAmount(cells[ci])
                    if v is not None:
                        nums.append(v)
                if not nums:
                    break
                result[field] = nums[0]  # 보통주 (하위호환)
                if includePreferred and field in _PREF_FIELDS:
                    # 우선주 식별: nums = [공통, 우선, 합계] 일 때만 우선주 인정.
                    # 합계 검증: |공통 + 우선 - 합계| / 합계 < 0.001
                    # 우선주 없는 종목은 보통 [공통, 공통] 또는 [공통, 합계=공통] → 우선주=0
                    pref = 0.0
                    if len(nums) >= 3:
                        c, p, t = nums[0], nums[1], nums[2]
                        if t > 0 and abs(c + p - t) / t < 0.001:
                            pref = p
                    result[_PREF_FIELDS[field]] = pref
                break

    if not result.get("outstandingShares"):
        return None
    return result


# pipeline
def shareCapital(stockCode: str) -> ShareCapitalResult | None:
    """사업보고서에서 주식의 총수 추출.

    Args:
        stockCode: 종목코드 (6자리)

    Returns:
        ShareCapitalResult 또는 데이터 부족 시 None

    Raises:
        없음.

    Example:
        >>> shareCapital(...)
    """
    df = loadData(stockCode)
    corpName = extractCorpName(df)

    years = sorted(df["year"].unique().to_list(), reverse=True)

    yearData: dict[int, dict] = {}

    for year in years:
        report = selectReport(df, year, reportKind="annual")
        if report is None:
            continue

        shareRows = report.filter(pl.col("section_title").str.contains("주식의 총수"))
        if shareRows.height == 0:
            continue

        reportYear = extractReportYear(shareRows["report_type"][0])
        if reportYear is None:
            continue

        content = shareRows["section_content"][0]
        parsed = parseShareCapitalTable(content)

        if parsed is None:
            continue

        if reportYear not in yearData:
            yearData[reportYear] = parsed

    if not yearData:
        return None

    latestYear = max(yearData.keys())
    latest = yearData[latestYear]

    records = []
    for yr in sorted(yearData.keys()):
        d = yearData[yr]
        records.append(
            {
                "year": yr,
                "outstandingShares": d.get("outstandingShares"),
                "treasuryShares": d.get("treasuryShares"),
                "floatingShares": d.get("floatingShares"),
                "treasuryRatio": d.get("treasuryRatio"),
            }
        )

    ts = pl.DataFrame(records)

    return ShareCapitalResult(
        corpName=corpName,
        nYears=ts.height,
        authorizedShares=latest.get("authorizedShares"),
        issuedShares=latest.get("issuedShares"),
        retiredShares=latest.get("retiredShares"),
        outstandingShares=latest.get("outstandingShares"),
        treasuryShares=latest.get("treasuryShares"),
        floatingShares=latest.get("floatingShares"),
        treasuryRatio=latest.get("treasuryRatio"),
        timeSeries=ts,
    )


# builder — cross-company sharesOutstanding scan parquet 빌더 (구 builder.py 통합)


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
    docsDir: "str | Path | None" = None,
    outputPath: "str | Path | None" = None,
    write: bool = True,
) -> "pl.DataFrame":
    """전 종목 docs glob → 발행주식수 DataFrame.

    Args:
        docsDir: docs parquet 디렉토리. None이면 ``data/dart/docs/``.
        outputPath: 출력 parquet 경로. None이면 ``data/dart/scan/sharesOutstanding.parquet``.
        write: True면 parquet 저장. False면 DataFrame 만 반환.

    Returns:
        발행주식수 DataFrame (rcept_date desc 정렬).

    Raises:
        FileNotFoundError: docs 디렉토리/parquet 부재.
        RuntimeError: 추출 결과 0 건.

    Example:
        >>> buildSharesOutstandingScan(...)
    """
    import logging
    from pathlib import Path

    from dartlab.core.dataLoader import _dataDir

    log = logging.getLogger(__name__)

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
            sub = (
                pl.scan_parquet(str(pf))
                .filter(pl.col("section_title") == _SECTION_TITLE)
                .select(keepCols)
                .collect(engine="streaming")
            )
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
