"""docs 슬림 cross-company 인덱스 빌더 — P3 (whimsical-marinating-axolotl 흡수).

전 종목 ``data/dart/docs/*.parquet`` 를 단일 슬림 parquet 으로 통합. 메타데이터만
(``section_content`` 제외) 보유해 cross-company 질문 ("X 섹션 보유 회사") 을
RSS <100 MB 로 1~2 초 내 답.

산출물 ``data/dart/scan/docsIndex.parquet`` schema:
    stockCode      Utf8           # 종목코드
    corpName       Utf8           # 회사명 (조회 편의)
    year           Int32          # 보고연도
    reportType     Categorical    # annual / Q1 / Q2 / Q3
    periodKey      Utf8           # "2024" / "2024Q1"
    sectionOrder   Int32          # 보고서 내 순서
    sectionTitle   Utf8           # 섹션 제목 (검색 대상)
    sectionUrl     Utf8           # DART 뷰어 직링크
    contentLength  UInt32         # section_content 글자 수 (헤더-only 판별용)
    hasTable       Boolean        # 본문에 markdown table 포함 여부
    docId          Utf8           # rcept_no

룰 8 (limit) + 룰 9 (raw cross-scan 차단) 충족 — Scan.docsSections() 가 본 인덱스 경유.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import polars as pl

log = logging.getLogger(__name__)

_DEFAULT_DOCS_PATTERN = "*.parquet"

_OUTPUT_SCHEMA: dict[str, type[pl.DataType]] = {
    "stockCode": pl.Utf8,
    "corpName": pl.Utf8,
    "year": pl.Int32,
    "reportType": pl.Utf8,  # cast to Categorical after concat
    "periodKey": pl.Utf8,
    "sectionOrder": pl.Int32,
    "sectionTitle": pl.Utf8,
    "sectionUrl": pl.Utf8,
    "contentLength": pl.UInt32,
    "hasTable": pl.Boolean,
    "docId": pl.Utf8,
}


def _chunked(iterable: list, n: int):
    """list 를 n 단위로 chunk."""
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def _periodKey(year: int, reportType: str) -> str:
    """(year, reportType) → "2024" / "2024Q1" 표기."""
    if reportType == "annual":
        return str(year)
    return f"{year}{reportType}"


def buildDocsIndex(
    *,
    sinceYear: int = 2016,
    batchSize: int = 100,
    docsDir: str | Path | None = None,
    outputPath: str | Path | None = None,
    verbose: bool = False,
) -> Path:
    """전 종목 docs parquet → 슬림 메타 인덱스 통합 빌드.

    Args:
        sinceYear: 시작 연도. 이전 보고서 제외 (volume 축소).
        batchSize: 한 번에 concat 할 parquet 파일 수. 메모리 압박 시 줄임.
        docsDir: ``data/dart/docs/`` 디렉토리. None 이면 기본 경로.
        outputPath: 산출 parquet 경로. None 이면 ``data/dart/scan/docsIndex.parquet``.
        verbose: 진행 로그 출력 여부.

    Returns:
        산출 parquet 절대 경로.

    Raises:
        FileNotFoundError: docs 디렉토리/parquet 부재.
        RuntimeError: 추출 결과 0 건.

    Example:
        >>> from dartlab.scan.builder.docsIndex import buildDocsIndex
        >>> path = buildDocsIndex(sinceYear=2020, batchSize=200, verbose=True)
        >>> print(path)
        .../data/dart/scan/docsIndex.parquet
    """
    from dartlab.core.dataLoader import _dataDir

    docsRoot = Path(docsDir) if docsDir else Path(_dataDir("docs"))
    if not docsRoot.exists():
        raise FileNotFoundError(f"docs 디렉토리 부재: {docsRoot}")

    parquetFiles = sorted(docsRoot.glob(_DEFAULT_DOCS_PATTERN))
    if not parquetFiles:
        raise FileNotFoundError(f"docs parquet 부재: {docsRoot}")

    if verbose:
        log.info(
            "[docsIndex] %d parquet 스캔 시작 (batchSize=%d, sinceYear=%d)", len(parquetFiles), batchSize, sinceYear
        )

    t0 = time.time()
    chunks: list[pl.DataFrame] = []
    failedFiles = 0
    totalRows = 0

    keepCols = [
        "stock_code",
        "corp_name",
        "year",
        "report_type",
        "section_order",
        "section_title",
        "section_url",
        "rcept_no",
    ]

    for batchIdx, batch in enumerate(_chunked(parquetFiles, batchSize)):
        batch_dfs: list[pl.DataFrame] = []
        for pf in batch:
            try:
                lf = pl.scan_parquet(str(pf)).filter(pl.col("year") >= sinceYear)
                # 본문 길이 + table 여부만 추출 → content drop
                df = lf.select(
                    keepCols
                    + [
                        pl.col("section_content").str.len_chars().cast(pl.UInt32).alias("contentLength"),
                        pl.col("section_content").str.contains(r"\|").alias("hasTable"),
                    ]
                ).collect(streaming=True)
            except (pl.exceptions.PolarsError, OSError):
                failedFiles += 1
                continue
            if df.is_empty():
                continue
            # 컬럼명 camelCase 정렬
            df = df.rename(
                {
                    "stock_code": "stockCode",
                    "corp_name": "corpName",
                    "report_type": "reportType",
                    "section_order": "sectionOrder",
                    "section_title": "sectionTitle",
                    "section_url": "sectionUrl",
                    "rcept_no": "docId",
                }
            )
            # year cast Int32
            df = df.with_columns(pl.col("year").cast(pl.Int32))
            # periodKey 생성
            df = df.with_columns(
                pl.when(pl.col("reportType") == "annual")
                .then(pl.col("year").cast(pl.Utf8))
                .otherwise(pl.col("year").cast(pl.Utf8) + pl.col("reportType"))
                .alias("periodKey")
            )
            df = df.select(list(_OUTPUT_SCHEMA.keys()))
            batch_dfs.append(df)
            totalRows += df.height

        if batch_dfs:
            chunks.append(pl.concat(batch_dfs, how="diagonal_relaxed"))
            if verbose:
                log.info("[docsIndex] batch %d 완료 (누적 row=%d)", batchIdx + 1, totalRows)

    if not chunks:
        raise RuntimeError("docs 인덱스 추출 결과 0 건")

    result = pl.concat(chunks, how="diagonal_relaxed")
    # reportType → Categorical (저장 size 절감)
    result = result.with_columns(pl.col("reportType").cast(pl.Categorical))

    if outputPath is None:
        scanDir = Path(_dataDir("scan"))
        scanDir.mkdir(parents=True, exist_ok=True)
        outputPath = scanDir / "docsIndex.parquet"
    outputPath = Path(outputPath)
    outputPath.parent.mkdir(parents=True, exist_ok=True)
    result.write_parquet(str(outputPath), compression="zstd", row_group_size=50_000)

    elapsed = time.time() - t0
    if verbose:
        sizeMb = outputPath.stat().st_size / 1024 / 1024
        log.info(
            "[docsIndex] %d rows · %d failedFiles · %.1f MB · %.1fs → %s",
            result.height,
            failedFiles,
            sizeMb,
            elapsed,
            outputPath,
        )

    return outputPath
