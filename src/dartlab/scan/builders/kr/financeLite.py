"""KR scan finance-lite parquet builder."""

from __future__ import annotations

import time
from pathlib import Path

import polars as pl

from dartlab.scan.builders.kr.common import say, scanDir


def buildFinanceLite(*, sinceYear: int | None = None, verbose: bool = True) -> Path | None:
    """pyodide 용 ``finance-lite.parquet`` 파생.

    Parameters:
        sinceYear: 포함할 최소 ``bsns_year``. None 이면 lite 기본값.
        verbose: 진행 로그 출력 여부.

    Returns:
        생성된 ``finance-lite.parquet`` 경로. 원본 없거나 결과 비면 None.

    Raises:
        polars.PolarsError: 원본 ``finance.parquet`` 손상 또는 write 실패 시.

    Examples:
        >>> p = buildFinanceLite(verbose=True)

    Guide:
        ``buildFinance`` 직후 pyodide/브라우저 로딩용 경량본을 만든다.

    Capabilities:
        finance 합본에서 lite 계정, 연도, 재무제표 구분만 lazy filter 후 zstd parquet 으로 저장.

    AIContext:
        브라우저 scan/account 호출이 메모리 한계 안에서 핵심 재무 계정을 조회하게 한다.

    When:
        prebuild 사이클에서 full finance parquet 생성 직후.

    How:
        ``LITE_ACCOUNTS`` 를 fast key synonym union 으로 확장하고 lazy filter/sink 한다.

    Requires:
        선행 ``finance.parquet`` 및 ``scan.io.lite`` 스펙.

    SeeAlso:
        ``buildFinance`` · ``LITE_ACCOUNTS``.
    """
    from dartlab.providers.dart.finance.scanAccount import _buildFastKeys
    from dartlab.scan.io.parquet import LITE_ACCOUNTS, LITE_SINCE_YEAR, LITE_SJ_DIVS

    effectiveSinceYear = LITE_SINCE_YEAR if sinceYear is None else sinceYear
    outDir = scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outputPath = outDir / "finance-lite.parquet"
    srcPath = outDir / "finance.parquet"

    if not srcPath.exists():
        if verbose:
            say("[finance-lite] finance.parquet 없음 → buildFinance 먼저 실행 필요")
        return None

    allKeys: set[str] = set()
    for sid in LITE_ACCOUNTS:
        allKeys.update(_buildFastKeys(sid))
    keysList = list(allKeys)

    if verbose:
        say(f"[finance-lite] {len(LITE_ACCOUNTS)}계정 → {len(keysList)}키, sinceYear={effectiveSinceYear}")

    t0 = time.perf_counter()
    keepCols = [
        "stockCode",
        "bsns_year",
        "reprt_nm",
        "sj_div",
        "fs_nm",
        "account_id",
        "account_nm",
        "thstrm_amount",
        "thstrm_add_amount",
    ]

    lf = (
        pl.scan_parquet(str(srcPath))
        .filter(pl.col("sj_div").is_in(list(LITE_SJ_DIVS)))
        .filter(pl.col("bsns_year").cast(pl.Int32, strict=False) >= effectiveSinceYear)
        .filter(pl.col("account_id").is_in(keysList) | pl.col("account_nm").is_in(keysList))
        .select(keepCols)
    )
    lf.sink_parquet(str(outputPath), compression="zstd")

    summary = (
        pl.scan_parquet(str(outputPath))
        .select(pl.len().alias("rows"), pl.col("stockCode").n_unique().alias("stocks"))
        .collect()
    )
    rows = int(summary["rows"][0])
    if rows == 0:
        outputPath.unlink(missing_ok=True)
        if verbose:
            say("[finance-lite] 결과 없음")
        return None

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    stocks = int(summary["stocks"][0])
    if verbose:
        say(f"[finance-lite] 완료: {stocks}종목, {rows:,}행, {diskMb:.1f}MB, {elapsed:.1f}초 → {outputPath.name}")

    return outputPath
