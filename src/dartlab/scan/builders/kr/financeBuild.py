"""KR scan finance parquet builder.

Capabilities:
    - Builds the normalized all-company finance parquet used by scan financial axes.

Args:
    Public entry points accept prebuild window and logging options.

Returns:
    ``Path`` for generated parquet or ``None`` when no source data exists.

Example:
    >>> from dartlab.scan.builders.kr.financeBuild import buildFinance
    >>> p = buildFinance(sinceYear=2021, verbose=True)

Guide:
    Keep finance-source normalization here. Lightweight browser derivatives stay in
    ``financeLite`` because they are consumer-specific filters over this output.

SeeAlso:
    ``fiscal``, ``financeLite``, and ``scan.io.parquet``.

Requires:
    Raw DART finance parquet files and bundled account mapping data.

AIContext:
    This module owns the canonical finance scan prebuild. Runtime analysis should
    consume its parquet output instead of re-implementing raw finance collection.

LLM Specifications:
    AntiPatterns: Do not add report/docs/share/valuation build logic here.
    OutputSchema: ``finance.parquet`` with normalized account and calendar columns.
    Prerequisites: Raw finance files under the configured data root.
    Freshness: Rebuilt by the scan prebuild workflow.
    Dataflow: raw finance parquet -> fiscal calendarization -> account mapping -> merged parquet.
    TargetMarkets: KR DART scan finance.
"""

from __future__ import annotations

import shutil
import time
from datetime import date
from pathlib import Path

import polars as pl

from dartlab.core.logger import getLogger
from dartlab.scan.builders.kr.common import BATCH_SIZE as _BATCH
from dartlab.scan.builders.kr.common import financeDir as _financeDir
from dartlab.scan.builders.kr.common import mergeBatchFiles as _mergeBatchFiles
from dartlab.scan.builders.kr.common import say as _say
from dartlab.scan.builders.kr.common import scanDir as _scanDir
from dartlab.scan.builders.kr.fiscal import _calendarizeFiscalColumns, _fiscalMonthMap

_log = getLogger(__name__)


def _loadAccountMap() -> dict[str, str]:
    """accountMappings.json → 계정명 매핑 로드.

    Returns
    -------
    dict[str, str]
        {원본계정명: snakeId} 매핑 (예: {"매출액": "sales"}).
    """
    import json

    # parents[3] = src/dartlab (scan/builders/kr/financeBuild.py → 3 단계 up)
    mapPath = Path(__file__).resolve().parents[3] / "reference" / "data" / "accountMappings.json"
    if not mapPath.exists():
        raise FileNotFoundError(f"필수 번들 리소스 누락: dartlab/reference/data/accountMappings.json ({mapPath})")
    data = json.loads(mapPath.read_text(encoding="utf-8"))
    mappings = data.get("mappings", {})
    if not isinstance(mappings, dict):
        raise ValueError(f"accountMappings.json mappings 필드가 dict 아님: {mapPath}")
    return mappings


def buildFinance(*, sinceYear: int = 2021, verbose: bool = True) -> Path | None:
    """finance/*.parquet → ``finance.parquet`` 합산 (결산월 환원 + 계정 정규화).

    가장 비싼 prebuild 단계. 종목별 raw parquet 을 순회하며 (1) 결산월 SSOT 기반 캘린더
    분기 환원, (2) accountMappings.json 으로 ``account_nm`` → ``account_id_std`` snakeId
    정규화. ~3964 종목 → 300+ MB 단일 합본 출력.

    Parameters
    ----------
    sinceYear : int
        포함할 최소 사업연도 (``bsns_year >= sinceYear``). 기본 2021. CI 매개변수.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 ``finance.parquet`` 경로. raw parquet 없으면 None.

    Raises
    ------
    polars.PolarsError
        finance parquet 손상 또는 ``sink_parquet`` 실패 시.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.financeBuild import buildFinance
    >>> p = buildFinance(sinceYear=2021, verbose=True)
    >>> p.exists() if p else "no data"

    Capabilities:
        - 종목별 raw finance parquet 을 단일 합본으로 정규화. 결산월 다른 회사 (10/3/6월) 의
          ``bsns_year``/``reprt_nm`` 을 캘린더 기준으로 환원해 횡단 비교 가능 형태로 변환.
        - 계정명 한글 → snakeId (예: "매출액" → "sales") 정규화로 다언어 라벨 안전.
        - 빌드 직후 ``_sanityCheckCalendarYears`` 로 ``bsns_year > today.year`` 회귀 자동 감지.

    AIContext:
        ``dartlab.scan("account", "매출액")`` · ``scan("ratio", "roe")`` · scan financial 6 축
        (profitability/growth/quality/...) 의 1 차 데이터 source. AI 가 횡단 재무 분석 호출 시
        본 빌드 산출물을 LazyFrame 으로 스캔하여 ``finance/sanity`` warning 이 있는 환경에서는
        결과 신뢰도가 떨어진다고 안내해야 한다.

    Guide:
        - 결산월 SSOT 우선순위: corp_profile (DART API) → listing (KIND) → rcept_no 추정 → 12 fallback.
          P-S11 이후 corp_profile 이 권위 SSOT. ``scripts/build/buildCorpProfile.py`` 가 매 prebuild
          전에 갱신 (신규 상장 / 결산월 변경 즉시 반영).
        - 비12월 결산 환원 실패 시 회계분기가 캘린더에 misplace (예: 10월 결산 사업연도 2026 4 분기
          → 잘못된 2025Q4 같은). sanity check 가 warning emit.

    When:
        매 prebuild 사이클 (KST 03:00 / 15:00, ``Data Sync.yml`` workflow 직후). 사용자가 직접
        호출하는 케이스: 로컬에 raw finance 다운로드 후 scan axis 호출 전.

    How:
        ``buildScan`` 의 두 번째 단계 (``buildChanges`` 직후). 종목당 파이프라인 = read_parquet →
        stockCode 컬럼 보강 → bsns_year 필터 → ``_calendarizeFiscalColumns`` → account_id_std 추가 →
        200 단위 배치 임시 청크 → ``_mergeBatchFiles`` (diagonal_relaxed). 매 종목 실패는 silent
        skip — `sink_parquet` segfault 가드를 위해 청크 파일 + diagonal merge 강행.

    Requires:
        - 로컬 ``data/dart/finance/{stockCode}.parquet`` (Data Sync 가 채움)
        - ``data/dart/scan/corpProfile.parquet`` (선택 — buildCorpProfile 가 갱신)
        - ``src/dartlab/reference/data/accountMappings.json`` (snakeId SSOT)

    SeeAlso:
        - :func:`_fiscalMonthMap` · :func:`_calendarizeFiscalColumns` · :func:`_sanityCheckCalendarYears`
        - :func:`_loadAccountMap` — accountMappings.json 로더
        - :func:`dartlab.scan.builders.kr.financeLite.buildFinanceLite`
        - :mod:`dartlab.scan.io.parquet` — 호출자측 LazyFrame 스캔/필터 헬퍼
    """
    finDir = _financeDir()
    outDir = _scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outputPath = outDir / "finance.parquet"
    batchDir = outDir / "_tmp_finance"
    batchDir.mkdir(parents=True, exist_ok=True)

    allFiles = sorted(finDir.glob("*.parquet"))
    if not allFiles:
        if verbose:
            _say("finance parquet 없음 — 빌드 건너뜀")
        return None

    acctMap = _loadAccountMap()
    if verbose and acctMap:
        _say(f"[finance] accountMappings: {len(acctMap)}개 매핑 로드")

    fmMap = _fiscalMonthMap()
    if verbose and fmMap:
        nonDec = sum(1 for m in fmMap.values() if m != 12)
        _say(f"[finance] 결산월 SSOT {len(fmMap)}종목 (비12월 {nonDec}) → 캘린더 분기 환원")

    if verbose:
        _say(f"[finance] {len(allFiles)}종목, sinceYear={sinceYear}")

    t0 = time.perf_counter()
    batchChunks: list[pl.DataFrame] = []
    success = 0
    totalRows = 0
    batchIdx = 0

    for i, pf in enumerate(allFiles):
        try:
            df = pl.read_parquet(str(pf))
        except (pl.exceptions.PolarsError, OSError):
            continue

        if "stockCode" not in df.columns and "stock_code" not in df.columns:
            df = df.with_columns(pl.lit(pf.stem).alias("stockCode"))
        elif "stock_code" in df.columns and "stockCode" not in df.columns:
            df = df.rename({"stock_code": "stockCode"})

        if "bsns_year" in df.columns:
            df = df.filter(pl.col("bsns_year").cast(pl.Utf8).str.to_integer(strict=False) >= sinceYear)

        if df.height == 0:
            continue

        code = pf.stem
        fm = fmMap.get(code, 12)
        if "bsns_year" in df.columns and "reprt_nm" in df.columns:
            df = _calendarizeFiscalColumns(df, fm)

        if acctMap and "account_nm" in df.columns:
            df = df.with_columns(
                pl.col("account_nm").replace_strict(acctMap, default=None, return_dtype=pl.Utf8).alias("account_id_std")
            )

        batchChunks.append(df)
        totalRows += df.height
        success += 1

        if len(batchChunks) >= _BATCH or i == len(allFiles) - 1:
            if batchChunks:
                batch = pl.concat(batchChunks, how="diagonal_relaxed")
                batch.write_parquet(str(batchDir / f"batch_{batchIdx:03d}.parquet"), compression="zstd")
                del batch
                batchChunks = []
                batchIdx += 1

        if verbose and (i + 1) % 500 == 0:
            _say(f"  [{i + 1}/{len(allFiles)}] {success}ok {totalRows:,}rows {time.perf_counter() - t0:.0f}s")

    if batchIdx == 0:
        if verbose:
            _say("  finance 결과 없음")
        shutil.rmtree(batchDir, ignore_errors=True)
        return None

    _mergeBatchFiles(batchDir, outputPath, how="diagonal_relaxed")
    shutil.rmtree(batchDir, ignore_errors=True)

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    if verbose:
        _say(f"  완료: {success}종목, {totalRows:,}행, {diskMb:.1f}MB, {elapsed:.0f}초")

    _sanityCheckCalendarYears(outputPath)

    return outputPath


def _sanityCheckCalendarYears(outputPath: Path) -> None:
    """빌드 결과 finance.parquet 의 캘린더 환원 sanity check.

    2026Q4 같은 misplace (결산월 환원 누락) 회귀를 빌드 직후 검출. raw 의 회계
    ``bsns_year`` 는 결산월 환원 후 캘린더 연도가 되어야 하므로 ``today.year`` 보다
    크면 비정상.

    Parameters
    ----------
    outputPath : Path
        빌드된 ``finance.parquet`` 경로.

    Notes
    -----
    - 위반 발견 시 warning 로그만 emit. 빌드 실패시키지 않음 — 사용자가 finance.parquet
      을 활용하면서 fallback 수정으로 후속 처리.
    - 정상 케이스: bsns_year ≤ today.year 모두 통과.
    """
    today = date.today()
    try:
        bad = (
            pl.scan_parquet(str(outputPath))
            .filter(pl.col("bsns_year").cast(pl.Int32, strict=False) > today.year)
            .select(["stockCode", "bsns_year", "reprt_nm"])
            .unique()
            .collect(engine="streaming")
        )
    except (pl.exceptions.PolarsError, OSError) as e:
        _log.warning(f"[finance/sanity] 검증 실패 (skip): {e}")
        return

    if bad.height > 0:
        _log.warning(
            f"[finance/sanity] bsns_year > {today.year} row {bad.height}개 발견 — "
            "결산월 환원 실패 의심. 비12월 결산 SSOT (_fiscalMonthMap) 확인 필요."
        )
        sample = bad.head(5).to_dicts()
        _log.warning(f"[finance/sanity] 비정상 샘플: {sample}")
