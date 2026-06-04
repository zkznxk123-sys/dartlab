"""docs 슬림 cross-company 인덱스 빌더 — P3 / P3.5.

전 종목 ``data/{provider}/docs/*.parquet`` 를 단일 슬림 parquet 으로 통합. 메타데이터만
(``section_content`` 제외) 보유해 cross-company 질문 ("X 섹션 보유 회사") 을
RSS <100 MB 로 1~2 초 내 답.

산출물 ``data/{provider}/scan/docsIndex.parquet`` schema:
    stockCode      Utf8           # 종목코드 (dart 6자리 / edgar ticker / edinet 4자리)
    corpName       Utf8           # 회사명 (조회 편의)
    year           Int32          # 보고연도
    reportType     Categorical    # annual / Q1 / Q2 / Q3
    periodKey      Utf8           # "2024" / "2024Q1"
    sectionOrder   Int32          # 보고서 내 순서
    sectionTitle   Utf8           # 섹션 제목 (검색 대상)
    sectionUrl     Utf8           # 외부 뷰어 직링크
    contentLength  UInt32         # section_content 글자 수 (헤더-only 판별용)
    hasTable       Boolean        # 본문에 markdown table 포함 여부
    docId          Utf8           # filing id (DART rcept_no / EDGAR accession / EDINET docId)

룰 8 (limit) + 룰 9 (raw cross-scan 차단) 충족 — Scan.docsSections() 가 본 인덱스 경유.

P3: DART (`buildDocsIndex`)
P3.5: EDGAR (`buildEdgarDocsIndex`) / EDINET (`buildEdinetDocsIndex`) — 동일 schema.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import polars as pl

from dartlab.core.memory import withMemoryBudget

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


@withMemoryBudget(limitMb=1000)
def buildDocsIndex(
    *,
    sinceYear: int = 2016,
    batchSize: int = 100,
    docsDir: str | Path | None = None,
    outputPath: str | Path | None = None,
    verbose: bool = False,
) -> Path:
    """전 종목 docs parquet → 슬림 메타 인덱스 통합 빌드 (P3, cross-company 1~2 초 응답).

    ``section_content`` 같은 본문 컬럼을 제외하고 메타만 (~제목·길이·URL·section_order)
    추출한 슬림 인덱스. cross-company 질문 ("X 섹션 보유 회사") 를 RSS <100 MB 로 1~2 초
    내 답하는 게 목표 — `Scan.docsSections()` 가 본 인덱스 경유 (룰 8 limit + 룰 9 raw
    cross-scan 차단).

    Args:
        sinceYear: 시작 연도. 이전 보고서 제외 (volume 축소).
        batchSize: 한 번에 concat 할 parquet 파일 수. 메모리 압박 시 줄임.
        docsDir: 본문 source 디렉토리 override. None 이면 KR 기본 = ``data/dart/panel/`` (panel 섹션).
        outputPath: 산출 parquet 경로. None 이면 ``data/dart/scan/docsIndex.parquet``.
        verbose: 진행 로그 출력 여부.

    Returns:
        산출 parquet 절대 경로.

    Raises:
        FileNotFoundError: docs 디렉토리/parquet 부재.
        RuntimeError: 추출 결과 0 건.

    Example:
        >>> from dartlab.scan.builders.kr.docsIndex import buildDocsIndex
        >>> path = buildDocsIndex(sinceYear=2020, batchSize=200, verbose=True)
        >>> print(path)
        .../data/dart/scan/docsIndex.parquet

    Capabilities:
        - 종목별 source parquet (panel 섹션, 수십~수백 MB) → 단일 슬림 parquet (~수십 MB) 으로 통합.
          ``_OUTPUT_SCHEMA`` 11 컬럼 — 본문 글자수 + 테이블 존재 여부만 보유.
        - ``withMemoryBudget(1000MB)`` 데코레이터로 RSS 한도 가드. ``batchSize`` 단위 chunked
          concat → 전체 단일 sink.

    AIContext:
        ``Scan.docsSections(market, sections, ...)`` 의 1 차 source. 사용자가 "이 섹션 가진
        회사 어디?" · "사외이사 정보 들어간 사업보고서 N건" 류 cross-company 질문 시 본 인덱스
        경유. 본문은 별도 `c.panel`(공시 수평화 보드) 회사 단위 회수로 필요시에만 fetch.

    Guide:
        - 출력 경로 default 는 dart-specific. EDGAR/EDINET 는 `buildEdgarDocsIndex` ·
          `buildEdinetDocsIndex` 가 동일 schema 로 별도 출력.
        - ``contentLength`` 컬럼이 header-only 섹션 (정의 없음) 판별의 필터 키.
        - 시계열 비교는 ``year`` 또는 ``periodKey`` 로.

    When:
        매 prebuild 사이클 (``buildScan`` 직후 별도 단계). `prebuildData.py` 의 `_buildDocsIndex`
        가 panel 캐시 있을 때만 호출. 로컬 직접 호출은 디버깅 / cross-company 분석 prototype 용.

    How:
        source 종목별 parquet 정렬 → `batchSize` 단위 chunk → 각 chunk read + 메타만 select →
        polars concat → 최종 sink_parquet (single output). 빈 결과는 RuntimeError 로 fail-fast.

    Requires:
        - 로컬 ``data/dart/panel/{stockCode}.parquet`` 들 (panel 섹션 본문, KR 기본 source)
        - ``dartlab.core.memory.withMemoryBudget`` (RSS 가드)

    SeeAlso:
        - :func:`buildEdgarDocsIndex` · :func:`buildEdinetDocsIndex` — 다국가 동일 schema
        - :func:`dartlab.scan.scanClass.Scan.docsSections` — 본 인덱스 소비자
        - :data:`_OUTPUT_SCHEMA` — 컬럼 contract
    """
    from dartlab.core.dataLoader import _dataDir
    from dartlab.core.listingResolver import getListingResolver
    from dartlab.providers.dart.sections import sectionTexts

    # docs.parquet 농장 은퇴 → providers.dart.sections(panel 섹션) SSOT. docsDir override 는
    # 하위호환(미지정 시 panel dir glob 으로 종목 enum).
    panelRoot = Path(docsDir) if docsDir else Path(_dataDir("panel"))
    if not panelRoot.exists():
        raise FileNotFoundError(f"panel 디렉토리 부재: {panelRoot}")

    codes = sorted(p.stem for p in panelRoot.glob(_DEFAULT_DOCS_PATTERN))
    if not codes:
        raise FileNotFoundError(f"panel parquet 부재: {panelRoot}")

    if verbose:
        log.info("[docsIndex] %d 종목 스캔 시작 (batchSize=%d, sinceYear=%d)", len(codes), batchSize, sinceYear)

    resolver = getListingResolver()
    t0 = time.time()
    chunks: list[pl.DataFrame] = []
    failedFiles = 0
    totalRows = 0

    for batchIdx, batch in enumerate(_chunked(codes, batchSize)):
        batch_dfs: list[pl.DataFrame] = []
        for code in batch:
            try:
                src = sectionTexts(code)
            except (pl.exceptions.PolarsError, OSError):
                failedFiles += 1
                continue
            if src is None or src.is_empty():
                continue
            corpName = (resolver.codeToName(code) if resolver else None) or ""
            # panel period(YYYYQn) → year + reportType(Q4=annual). blockOrder=sectionOrder,
            # rceptNo=docId. panel 은 section_url 없음(빈 문자열). hasTable=raw XML <TABLE>.
            df = src.with_columns(
                pl.col("period").str.slice(0, 4).cast(pl.Int32, strict=False).alias("year"),
                pl.when(pl.col("period").str.slice(4) == "Q4")
                .then(pl.lit("annual"))
                .otherwise(pl.col("period").str.slice(4))
                .alias("reportType"),
            )
            df = df.filter(pl.col("year") >= sinceYear)
            if df.is_empty():
                continue
            df = df.with_columns(
                pl.lit(code).alias("stockCode"),
                pl.lit(corpName).alias("corpName"),
                pl.when(pl.col("reportType") == "annual")
                .then(pl.col("year").cast(pl.Utf8))
                .otherwise(pl.col("year").cast(pl.Utf8) + pl.col("reportType"))
                .alias("periodKey"),
                pl.col("blockOrder").cast(pl.Int32).alias("sectionOrder"),
                pl.col("sectionLeaf").alias("sectionTitle"),
                pl.lit("").alias("sectionUrl"),
                pl.col("contentRaw").str.len_chars().cast(pl.UInt32).alias("contentLength"),
                pl.col("contentRaw").str.contains("<TABLE", literal=True).alias("hasTable"),
                pl.col("rceptNo").alias("docId"),
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


# ─── P3.5: EDGAR / EDINET 빌더 (동일 schema, 다른 docs 디렉토리) ──────


def buildEdgarDocsIndex(
    *,
    sinceYear: int = 2016,
    batchSize: int = 100,
    docsDir: str | Path | None = None,
    outputPath: str | Path | None = None,
    verbose: bool = False,
) -> Path:
    """EDGAR docs parquet → 슬림 메타 인덱스 (P3.5, DART 와 schema 동일).

    `buildDocsIndex` 의 EDGAR provider wrapper. docsDir/outputPath default 만 다르고
    실제 추출 로직은 동일. ticker 단위 stockCode + accession 단위 docId.

    Args:
        sinceYear: 시작 연도. 이전 filing 제외.
        batchSize: concat 단위.
        docsDir: ``data/edgar/docs/`` 디렉토리. None 이면 기본 경로.
        outputPath: 산출 parquet 경로. None 이면 ``data/edgar/scan/docsIndex.parquet``.
        verbose: 진행 로그.

    Returns:
        산출 parquet 절대 경로.

    Raises:
        FileNotFoundError: docs 디렉토리/parquet 부재.
        RuntimeError: 추출 결과 0 건.

    Example:
        >>> from dartlab.scan.builders.kr.docsIndex import buildEdgarDocsIndex
        >>> path = buildEdgarDocsIndex(sinceYear=2020, verbose=True)

    Capabilities:
        - EDGAR docs parquet 컬렉션을 동일 11-컬럼 슬림 schema 로 통합.
        - `buildDocsIndex` 로 위임 — 컬럼 schema 단일화 (cross-market 횡단 query 호환).

    AIContext:
        ``Scan.docsSections("us", ...)`` 의 EDGAR source. AI agent 가 한국/미국 비교 분석 시
        동일 schema 라 양쪽 인덱스를 union 으로 다룰 수 있다.

    Guide:
        - DART 와 schema 호환되지만 stockCode 의미는 다름 (ticker vs 6 자리). corpName 으로 매핑.
        - filing 단위 = 10-K / 10-Q / 8-K, reportType 으로 구분.

    When:
        EDGAR provider prebuild 단계. dart 와 별도 cron / 별도 raw download 흐름.

    How:
        docsDir·outputPath default 보정 후 `buildDocsIndex` 위임. EDGAR raw schema 는 이미
        `_OUTPUT_SCHEMA` 와 호환되도록 EDGAR provider extractor 가 정규화.

    Requires:
        - ``data/edgar/docs/`` 디렉토리 (EDGAR Data Sync 결과)

    SeeAlso:
        - :func:`buildDocsIndex` — 본 wrapper 의 위임 대상
        - :func:`buildEdinetDocsIndex` — 일본 시장 동일 schema
    """
    from dartlab.core.dataLoader import _getDataRoot

    if docsDir is None:
        docsDir = _getDataRoot() / "edgar" / "docs"
    if outputPath is None:
        scanDir = _getDataRoot() / "edgar" / "scan"
        scanDir.mkdir(parents=True, exist_ok=True)
        outputPath = scanDir / "docsIndex.parquet"

    return buildDocsIndex(
        sinceYear=sinceYear,
        batchSize=batchSize,
        docsDir=docsDir,
        outputPath=outputPath,
        verbose=verbose,
    )


def buildEdinetDocsIndex(
    *,
    sinceYear: int = 2016,
    batchSize: int = 100,
    docsDir: str | Path | None = None,
    outputPath: str | Path | None = None,
    verbose: bool = False,
) -> Path:
    """EDINET docs parquet → 슬림 메타 인덱스 (P3.5, DART/EDGAR 와 schema 동일).

    Args:
        sinceYear: 시작 연도.
        batchSize: concat 단위.
        docsDir: ``data/edinet/docs/`` 디렉토리.
        outputPath: 산출 ``data/edinet/scan/docsIndex.parquet``.
        verbose: 진행 로그.

    Returns:
        산출 parquet 절대 경로.

    Raises:
        FileNotFoundError: docs 디렉토리/parquet 부재.
        RuntimeError: 추출 결과 0 건.

    Example:
        >>> from dartlab.scan.builders.kr.docsIndex import buildEdinetDocsIndex
        >>> path = buildEdinetDocsIndex(sinceYear=2020, verbose=True)

    Capabilities:
        - EDINET docs parquet → 동일 11-컬럼 슬림 schema. 4 자리 종목코드 + EDINET docId.

    AIContext:
        ``Scan.docsSections("jp", ...)`` 의 source. 한국·미국·일본 cross-market 비교 분석 시
        union 으로 다룰 수 있는 동일 schema 보장.

    Guide:
        - 메모리 룰 ``feedback_edinet_api_unavailable`` 참조 — EDINET API 통신 불가 환경에서는
          호출 자체가 의미 없다 (raw docs 자체가 없음). prebuild 도 skip.

    When:
        EDINET raw docs 가 채워진 환경에서만. 현재 통신 불가 (대부분 환경) 라 prebuild 에서
        실질 미실행.

    How:
        docsDir·outputPath default 보정 후 `buildDocsIndex` 위임.

    Requires:
        - ``data/edinet/docs/`` 디렉토리 (EDINET Data Sync — 현재 미작동)

    SeeAlso:
        - :func:`buildDocsIndex` · :func:`buildEdgarDocsIndex` — 동일 schema sibling
    """
    from dartlab.core.dataLoader import _getDataRoot

    if docsDir is None:
        docsDir = _getDataRoot() / "edinet" / "docs"
    if outputPath is None:
        scanDir = _getDataRoot() / "edinet" / "scan"
        scanDir.mkdir(parents=True, exist_ok=True)
        outputPath = scanDir / "docsIndex.parquet"

    return buildDocsIndex(
        sinceYear=sinceYear,
        batchSize=batchSize,
        docsDir=docsDir,
        outputPath=outputPath,
        verbose=verbose,
    )
