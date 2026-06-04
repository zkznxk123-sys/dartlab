"""KR scan changes parquet builder."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import polars as pl

from dartlab.scan.builders.kr.common import BATCH_SIZE, mergeBatchFiles, panelDir, say, scanDir


def _buildRawChanges(stockCode: str, sinceYear: int = 2021) -> pl.DataFrame | None:
    """panel 섹션 본문 → section 단위 변화 감지 (providers.dart.sections SSOT).

    Parameters:
        stockCode: 종목코드.
        sinceYear: 시작 연도. 이전 연도는 비교 기준으로만 사용.

    Returns:
        section 변화 DataFrame. 변화 없거나 입력 부적합이면 None.

    Raises:
        없음 — 본문 부재와 필수 컬럼 누락은 None 으로 흡수한다.

    Examples:
        >>> _buildRawChanges("005930")

    Guide:
        sectionLeaf 별 직전 period 대비 content hash/크기/숫자 제거 문자열을 비교한다.

    Capabilities:
        appeared/disappeared/numeric/structural/wording 변화 유형 분류.

    AIContext:
        disclosureRisk/dividendTrend scan 축이 사업보고서 서술 변화 신호를 읽는 원천.

    When:
        ``buildChanges`` 가 종목별 panel 본문을 순회할 때.

    How:
        sectionLeaf 기준 period shift 후 변경 row 만 추출해 표준 컬럼으로 select.

    Requires:
        panel artifact (providers.dart.sections.sectionTexts: sectionLeaf · contentRaw · period).

    SeeAlso:
        ``buildChanges`` · ``dartlab.providers.dart.sections.sectionTexts``.
    """
    from dartlab.providers.dart.sections import sectionTexts

    df = sectionTexts(stockCode)
    if df is None or df.is_empty():
        return None

    # 같은 (sectionLeaf, period) 블록 결합 → 섹션 1행. period → year(4자리) 파생.
    work = df.group_by(["sectionLeaf", "period"]).agg(pl.col("contentRaw").str.join("\n").alias("section_content"))
    work = work.with_columns(
        pl.col("period").str.slice(0, 4).cast(pl.Int64, strict=False).alias("year"),
        pl.col("sectionLeaf").alias("section_title"),
    )
    work = work.filter(pl.col("year") >= sinceYear - 1)
    if work.height < 2:
        return None

    work = work.sort(["section_title", "period"])

    work = work.with_columns(
        [
            pl.col("period").shift(1).over(["section_title"]).alias("_prevYear"),
            pl.col("section_content").shift(1).over(["section_title"]).alias("_prevContent"),
        ]
    )

    work = work.with_columns(
        [
            pl.col("section_content").hash().alias("_hash"),
            pl.col("_prevContent").hash().alias("_prevHash"),
            pl.col("section_content").str.len_chars().alias("sizeB"),
            pl.col("_prevContent").str.len_chars().alias("sizeA"),
            pl.col("section_content").str.slice(0, 200).alias("preview"),
        ]
    )

    changes = work.filter(
        pl.col("_prevYear").is_not_null()
        & ~(pl.col("section_content").is_null() & pl.col("_prevContent").is_null())
        & (
            (pl.col("_hash") != pl.col("_prevHash"))
            | pl.col("section_content").is_null()
            | pl.col("_prevContent").is_null()
        )
    )

    if changes.height == 0:
        return None

    numPattern = r"[\d,.]+"
    changes = changes.with_columns(
        [
            pl.col("section_content").str.replace_all(numPattern, "N").alias("_stripped"),
            pl.col("_prevContent").str.replace_all(numPattern, "N").alias("_prevStripped"),
        ]
    )

    changes = changes.with_columns(
        pl.when(pl.col("_prevContent").is_null())
        .then(pl.lit("appeared"))
        .when(pl.col("section_content").is_null())
        .then(pl.lit("disappeared"))
        .when(pl.col("_stripped") == pl.col("_prevStripped"))
        .then(pl.lit("numeric"))
        .when(
            (pl.col("sizeA") > 0)
            & (
                (pl.col("sizeB").cast(pl.Int64) - pl.col("sizeA").cast(pl.Int64)).abs().cast(pl.Float64)
                / pl.col("sizeA").cast(pl.Float64)
                > 0.5
            )
        )
        .then(pl.lit("structural"))
        .otherwise(pl.lit("wording"))
        .alias("changeType")
    )

    changes = changes.filter(pl.col("year") >= sinceYear)

    return changes.select(
        [
            pl.col("_prevYear").alias("fromPeriod"),
            pl.col("period").alias("toPeriod"),
            pl.col("section_title").alias("sectionTitle"),
            pl.col("changeType"),
            pl.col("sizeA"),
            pl.col("sizeB"),
            (pl.col("sizeB").cast(pl.Int64) - pl.col("sizeA").cast(pl.Int64)).alias("sizeDelta"),
            pl.col("preview"),
            pl.lit(stockCode).alias("stockCode"),
        ]
    )


def buildChanges(*, sinceYear: int = 2021, verbose: bool = True) -> Path | None:
    """docs/*.parquet → ``changes.parquet`` 프리빌드.

    Parameters:
        sinceYear: 시작 연도. 이전 연도는 비교 baseline 으로만 사용.
        verbose: 진행 로그 출력 여부.

    Returns:
        생성된 ``changes.parquet`` 경로. docs 데이터 없으면 None.

    Raises:
        polars.PolarsError: parquet write/merge 실패 시.

    Examples:
        >>> p = buildChanges(sinceYear=2021, verbose=True)

    Guide:
        scan prebuild 의 docs 변화 감지 전용 단계다.

    Capabilities:
        전종목 docs 변화 row 를 배치 parquet 으로 쓴 뒤 단일 ``changes.parquet`` 로 합산.

    AIContext:
        AI agent 가 disclosureRisk/dividendTrend 를 호출할 때 선행 리스크 신호 원천이 된다.

    When:
        Data Sync 직후 prebuild 단계 또는 로컬 raw docs 준비 이후.

    How:
        panel parquet 순회 → ``_buildRawChanges``(providers.dart.sections) → 200 단위 batch → final merge.

    Requires:
        로컬 ``data/dart/panel/{stockCode}.parquet``.

    SeeAlso:
        ``_buildRawChanges`` · ``buildScan``.
    """
    panelDirValue = panelDir()
    outDir = scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outputPath = outDir / "changes.parquet"
    batchDir = outDir / "_tmp_changes"
    batchDir.mkdir(parents=True, exist_ok=True)

    allFiles = sorted(panelDirValue.glob("*.parquet"))
    if not allFiles:
        if verbose:
            say("panel parquet 없음 — changes 빌드 건너뜀")
        return None

    if verbose:
        say(f"[changes] {len(allFiles)}종목, sinceYear={sinceYear}")

    t0 = time.perf_counter()
    batchChunks: list[pl.DataFrame] = []
    success = 0
    failed = 0
    totalRows = 0
    batchIdx = 0

    for i, pf in enumerate(allFiles):
        result = _buildRawChanges(pf.stem, sinceYear)
        if result is not None and result.height > 0:
            batchChunks.append(result)
            totalRows += result.height
            success += 1
        else:
            failed += 1

        if len(batchChunks) >= BATCH_SIZE or i == len(allFiles) - 1:
            if batchChunks:
                batch = pl.concat(batchChunks)
                batch.write_parquet(str(batchDir / f"batch_{batchIdx:03d}.parquet"), compression="zstd")
                del batch
                batchChunks = []
                batchIdx += 1

        if verbose and (i + 1) % 500 == 0:
            say(
                f"  [{i + 1}/{len(allFiles)}] {success}ok {failed}fail {totalRows:,}rows {time.perf_counter() - t0:.0f}s"
            )

    if batchIdx == 0:
        if verbose:
            say("  changes 결과 없음")
        shutil.rmtree(batchDir, ignore_errors=True)
        return None

    mergeBatchFiles(batchDir, outputPath)
    shutil.rmtree(batchDir, ignore_errors=True)

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    if verbose:
        say(f"  완료: {success}종목, {totalRows:,}행, {diskMb:.1f}MB, {elapsed:.0f}초")

    return outputPath
