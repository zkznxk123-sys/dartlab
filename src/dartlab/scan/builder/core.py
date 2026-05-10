"""전종목 scan 프리빌드 빌더.

docs → changes, finance → 합산, report → apiType별 분리.
실험 014/015에서 검증된 로직을 프로덕션화.
배치를 중간 파일로 쓰고 마지막에 합산하여 segfault 방지.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import polars as pl

# scanner에서 실제 사용하는 apiType 12개
SCAN_API_TYPES = [
    "majorHolder",
    "executive",
    "employee",
    "executivePayAllTotal",
    "executivePayIndividual",
    "auditOpinion",
    "dividend",
    "treasuryStock",
    "capitalChange",
    "corporateBond",
    "outsideDirector",
    "minorityHolder",
]

_BATCH = 200


def _fiscalMonthMap() -> dict[str, int]:
    """종목코드 → 결산월(int) 매핑.

    12월 결산은 포함하지 않음 (기본값이므로).
    listing + 데이터 패턴 양쪽에서 비12월 결산을 판별.

    Returns
    -------
    dict[str, int]
        {종목코드: 결산월} — 비12월 결산 종목만 포함 (예: {"035720": 3}).
    """
    result: dict[str, int] = {}

    # 1. listing 기반
    try:
        from dartlab.gather.listing import getKindList

        li = getKindList()
        if li is not None and not li.is_empty():
            if "결산월" in li.columns and "종목코드" in li.columns:
                nonDec = li.filter(pl.col("결산월") != "12월")
                for row in nonDec.select(["종목코드", "결산월"]).iter_rows():
                    code, month_str = row
                    try:
                        result[code] = int(month_str.replace("월", ""))
                    except (ValueError, AttributeError):
                        pass
    except (ImportError, FileNotFoundError, OSError):
        pass

    # 2. 데이터 기반 — listing에 없는 종목(상폐 등)은 bsns_year 패턴으로 추론
    from datetime import date

    today = date.today()
    calYear = today.year
    # 12월 결산이면 4월 현재 maxBsnsYear=작년(2025)
    maxBsnsYear12 = str(calYear - 1) if today.month <= 4 else str(calYear)

    finDir = _financeDir()
    if finDir.exists():
        for pf in finDir.glob("*.parquet"):
            code = pf.stem
            if code in result:
                continue  # listing에서 이미 파악
            try:
                lz = pl.scan_parquet(str(pf))
                if "bsns_year" not in lz.collect_schema().names():
                    continue
                maxYear = lz.select(pl.col("bsns_year").cast(pl.Utf8).max()).collect().item()
                if maxYear is not None and maxYear > maxBsnsYear12:
                    # 정확한 결산월은 모르지만, 비12월 결산 확정
                    # 보수적으로 6월(가장 흔한 비12월)로 추정
                    result[code] = 6
            except (pl.exceptions.PolarsError, OSError):
                continue

    return result


def _toCalendarPeriod(bsnsYear: int, fiscalQ: int, fiscalMonth: int) -> tuple[int, int]:
    """사업연도 분기 → 달력 (연도, 분기) 변환.

    Parameters
    ----------
    bsnsYear : int
        사업연도 (예: 2026).
    fiscalQ : int
        사업연도 분기 (1~4).
    fiscalMonth : int
        결산월 (1~12).

    Returns
    -------
    tuple[int, int]
        (calYear, calQ) — 달력 연도와 분기.

    Examples
    --------
    3월 결산(M=3), bsns_year=2026:
    Q1→2025Q2, Q2→2025Q3, Q3→2025Q4, Q4→2026Q1.
    """
    import math

    endMonth = (fiscalMonth + fiscalQ * 3) % 12
    if endMonth == 0:
        endMonth = 12
    calQ = math.ceil(endMonth / 3)
    calYear = bsnsYear - 1 if endMonth > fiscalMonth else bsnsYear
    return calYear, calQ


def _scanDir() -> Path:
    """scan 출력 디렉토리."""
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("scan"))


def _docsDir() -> Path:
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("docs"))


def _financeDir() -> Path:
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("finance"))


def _reportDir() -> Path:
    from dartlab.core.dataLoader import _dataDir

    return Path(_dataDir("report"))


def _say(msg: str) -> None:
    _log.info(msg)


def _mergeBatchFiles(batchDir: Path, outputPath: Path, *, how: str = "vertical") -> int:
    """배치 parquet 파일들을 1개로 합산.

    Parameters
    ----------
    batchDir : Path
        배치 파일 디렉토리 (batch_*.parquet).
    outputPath : Path
        합산 결과 저장 경로.
    how : str
        concat 방식 ("vertical" | "diagonal").

    Returns
    -------
    int
        합산된 총 행 수.
    """
    batchFiles = sorted(batchDir.glob("batch_*.parquet"))
    if not batchFiles:
        return 0

    parts = [pl.read_parquet(str(f)) for f in batchFiles]
    merged = pl.concat(parts, how=how)
    merged.write_parquet(str(outputPath), compression="zstd")
    totalRows = merged.height
    del merged, parts
    return totalRows


# ── changes ──────────────────────────────────────────────────────────


def _buildRawChanges(parquetPath: Path, stockCode: str, sinceYear: int = 2021) -> pl.DataFrame | None:
    """raw docs parquet → section 단위 변화 감지.

    Parameters
    ----------
    parquetPath : Path
        종목별 docs parquet 경로.
    stockCode : str
        종목코드.
    sinceYear : int
        시작 연도 (이전 연도는 비교 기준으로만 사용).

    Returns
    -------
    pl.DataFrame | None
        fromPeriod : str — 이전 기간
        toPeriod : str — 현재 기간
        sectionTitle : str — 변경 섹션명
        changeType : str — 변화 유형 (appeared/disappeared/numeric/structural/wording)
        sizeA : int — 이전 크기 (문자수)
        sizeB : int — 현재 크기 (문자수)
        sizeDelta : int — 크기 변화량 (문자수)
        preview : str — 현재 내용 미리보기 (200자)
        stockCode : str — 종목코드
        변화 없으면 None.
    """
    try:
        raw = pl.read_parquet(str(parquetPath))
    except (pl.exceptions.PolarsError, OSError):
        return None

    needed = {"year", "section_order", "section_title", "section_content"}
    if not needed.issubset(set(raw.columns)):
        return None

    raw = raw.filter(pl.col("year").cast(pl.Utf8).str.to_integer(strict=False) >= sinceYear - 1)
    if raw.height < 2:
        return None

    work = raw.select(["year", "section_order", "section_title", "section_content"])
    work = work.sort(["section_order", "section_title", "year"])

    work = work.with_columns(
        [
            pl.col("year").shift(1).over(["section_order", "section_title"]).alias("_prevYear"),
            pl.col("section_content").shift(1).over(["section_order", "section_title"]).alias("_prevContent"),
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

    changes = changes.filter(pl.col("year").cast(pl.Utf8).str.to_integer(strict=False) >= sinceYear)

    return changes.select(
        [
            pl.col("_prevYear").alias("fromPeriod"),
            pl.col("year").alias("toPeriod"),
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
    """docs → changes 프리빌드.

    Parameters
    ----------
    sinceYear : int
        시작 연도.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 changes.parquet 경로. 데이터 없으면 None.
    """
    docsDir = _docsDir()
    outDir = _scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outputPath = outDir / "changes.parquet"
    batchDir = outDir / "_tmp_changes"
    batchDir.mkdir(parents=True, exist_ok=True)

    allFiles = sorted(docsDir.glob("*.parquet"))
    if not allFiles:
        if verbose:
            _say("docs parquet 없음 — changes 빌드 건너뜀")
        return None

    if verbose:
        _say(f"[changes] {len(allFiles)}종목, sinceYear={sinceYear}")

    t0 = time.perf_counter()
    batchChunks: list[pl.DataFrame] = []
    success = 0
    failed = 0
    totalRows = 0
    batchIdx = 0

    for i, pf in enumerate(allFiles):
        result = _buildRawChanges(pf, pf.stem, sinceYear)
        if result is not None and result.height > 0:
            batchChunks.append(result)
            totalRows += result.height
            success += 1
        else:
            failed += 1

        if len(batchChunks) >= _BATCH or i == len(allFiles) - 1:
            if batchChunks:
                batch = pl.concat(batchChunks)
                batch.write_parquet(str(batchDir / f"batch_{batchIdx:03d}.parquet"), compression="zstd")
                del batch
                batchChunks = []
                batchIdx += 1

        if verbose and (i + 1) % 500 == 0:
            _say(
                f"  [{i + 1}/{len(allFiles)}] {success}ok {failed}fail {totalRows:,}rows {time.perf_counter() - t0:.0f}s"
            )

    if batchIdx == 0:
        if verbose:
            _say("  changes 결과 없음")
        shutil.rmtree(batchDir, ignore_errors=True)
        return None

    _mergeBatchFiles(batchDir, outputPath)
    shutil.rmtree(batchDir, ignore_errors=True)

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    if verbose:
        _say(f"  완료: {success}종목, {totalRows:,}행, {diskMb:.1f}MB, {elapsed:.0f}초")

    return outputPath


# ── finance ──────────────────────────────────────────────────────────


def _loadAccountMap() -> dict[str, str]:
    """accountMappings.json → 계정명 매핑 로드.

    Returns
    -------
    dict[str, str]
        {원본계정명: snakeId} 매핑 (예: {"매출액": "sales"}).
    """
    import json

    mapPath = Path(__file__).resolve().parents[1] / "core" / "data" / "accountMappings.json"
    if not mapPath.exists():
        return {}
    try:
        data = json.loads(mapPath.read_text(encoding="utf-8"))
        return data.get("mappings", {})
    except (json.JSONDecodeError, OSError):
        return {}


def buildFinance(*, sinceYear: int = 2021, verbose: bool = True) -> Path | None:
    """finance 전종목 합산 프리빌드.

    Parameters
    ----------
    sinceYear : int
        시작 연도.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 finance.parquet 경로. 데이터 없으면 None.
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

    # 계정명 정규화 매핑 로드
    acctMap = _loadAccountMap()
    if verbose and acctMap:
        _say(f"[finance] accountMappings: {len(acctMap)}개 매핑 로드")

    # 비12월 결산 종목 → 달력 분기 변환 준비
    fmMap = _fiscalMonthMap()
    if verbose and fmMap:
        _say(f"[finance] 비12월 결산 {len(fmMap)}종목 → 달력 분기 변환")

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

        # 비12월 결산 → bsns_year/reprt_nm을 달력 기준으로 변환
        code = pf.stem
        if code in fmMap and "bsns_year" in df.columns and "reprt_nm" in df.columns:
            fm = fmMap[code]
            _FQ_MAP = {"1분기": 1, "2분기": 2, "3분기": 3, "4분기": 4}
            rows = []
            for row in df.iter_rows(named=True):
                fq = _FQ_MAP.get(row["reprt_nm"])
                if fq is not None:
                    try:
                        calY, calQ = _toCalendarPeriod(int(row["bsns_year"]), fq, fm)
                        r = dict(row)
                        r["bsns_year"] = str(calY)
                        r["reprt_nm"] = f"{calQ}분기"
                        rows.append(r)
                    except (ValueError, TypeError):
                        rows.append(row)
                else:
                    rows.append(row)
            df = pl.DataFrame(rows, schema=df.schema)

        # 계정명 정규화: account_nm → snakeId 컬럼 추가
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

    return outputPath


# ── report ───────────────────────────────────────────────────────────


def buildReport(*, sinceYear: int = 2021, verbose: bool = True) -> list[Path]:
    """report → apiType별 분리 parquet 프리빌드.

    Parameters
    ----------
    sinceYear : int
        시작 연도.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    list[Path]
        생성된 apiType별 parquet 경로 목록.
    """
    repDir = _reportDir()
    outDir = _scanDir() / "report"
    outDir.mkdir(parents=True, exist_ok=True)

    allFiles = sorted(repDir.glob("*.parquet"))
    if not allFiles:
        if verbose:
            _say("report parquet 없음 — 빌드 건너뜀")
        return []

    if verbose:
        _say(f"[report] {len(allFiles)}종목 → apiType별 분리")

    t0 = time.perf_counter()

    # apiType별 배치 디렉토리
    apiBatchDirs: dict[str, Path] = {}
    apiBatchIdx: dict[str, int] = {}
    apiChunks: dict[str, list[pl.DataFrame]] = {}
    apiRows: dict[str, int] = {}
    for at in SCAN_API_TYPES:
        bd = outDir / f"_tmp_{at}"
        bd.mkdir(parents=True, exist_ok=True)
        apiBatchDirs[at] = bd
        apiBatchIdx[at] = 0
        apiChunks[at] = []
        apiRows[at] = 0

    processed = 0

    for i, pf in enumerate(allFiles):
        try:
            df = pl.read_parquet(str(pf))
        except (pl.exceptions.PolarsError, OSError):
            continue

        if "apiType" not in df.columns:
            continue

        if "stockCode" not in df.columns and "stock_code" not in df.columns:
            df = df.with_columns(pl.lit(pf.stem).alias("stockCode"))

        if "year" in df.columns:
            df = df.with_columns(pl.col("year").cast(pl.Utf8).str.to_integer(strict=False).alias("_yearInt"))
            df = df.filter(pl.col("_yearInt").is_null() | (pl.col("_yearInt") >= sinceYear)).drop("_yearInt")

        processed += 1

        for apiType in SCAN_API_TYPES:
            sub = df.filter(pl.col("apiType") == apiType)
            if sub.height > 0:
                apiChunks[apiType].append(sub)
                apiRows[apiType] += sub.height

                if len(apiChunks[apiType]) >= _BATCH:
                    batch = pl.concat(apiChunks[apiType], how="diagonal_relaxed")
                    idx = apiBatchIdx[apiType]
                    batch.write_parquet(
                        str(apiBatchDirs[apiType] / f"batch_{idx:03d}.parquet"),
                        compression="zstd",
                    )
                    del batch
                    apiChunks[apiType] = []
                    apiBatchIdx[apiType] = idx + 1

        if verbose and (i + 1) % 500 == 0:
            _say(f"  [{i + 1}/{len(allFiles)}] {processed}ok {time.perf_counter() - t0:.0f}s")

    # 남은 청크 flush + 합산
    outputs: list[Path] = []
    for apiType in SCAN_API_TYPES:
        # 남은 청크 쓰기
        if apiChunks[apiType]:
            batch = pl.concat(apiChunks[apiType], how="diagonal_relaxed")
            idx = apiBatchIdx[apiType]
            batch.write_parquet(
                str(apiBatchDirs[apiType] / f"batch_{idx:03d}.parquet"),
                compression="zstd",
            )
            del batch
            apiBatchIdx[apiType] = idx + 1

        if apiBatchIdx[apiType] == 0:
            shutil.rmtree(apiBatchDirs[apiType], ignore_errors=True)
            continue

        outPath = outDir / f"{apiType}.parquet"
        _mergeBatchFiles(apiBatchDirs[apiType], outPath, how="diagonal_relaxed")
        shutil.rmtree(apiBatchDirs[apiType], ignore_errors=True)

        diskMb = outPath.stat().st_size / 1024 / 1024
        outputs.append(outPath)
        if verbose:
            _say(f"  {apiType}: {apiRows[apiType]:,}행, {diskMb:.1f}MB")

    elapsed = time.perf_counter() - t0
    if verbose:
        _say(f"  report 완료: {len(outputs)}개 apiType, {elapsed:.0f}초")

    return outputs


# ── 전체 빌드 ────────────────────────────────────────────────────────


def _buildSharesOutstandingSafe(*, verbose: bool = True) -> Path | None:
    """발행주식수 풀 빌드 — 실패해도 전체 scan 진행.

    Returns
    -------
    Path | None
        생성된 sharesOutstanding.parquet 경로. 실패 시 None.
    """
    try:
        from dartlab.providers.dart.docs.finance.shareCapital.builder import buildSharesOutstandingScan

        if verbose:
            _say("[shares] 발행주식수 풀 빌드 시작")
        df = buildSharesOutstandingScan()
        if verbose:
            _say(f"[shares] 완료: rows={df.height} stocks={df['stock_code'].n_unique()}")
        return _scanDir() / "sharesOutstanding.parquet"
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        if verbose:
            _say(f"[shares] 실패: {exc}")
        return None


def buildFinanceLite(*, sinceYear: int | None = None, verbose: bool = True) -> Path | None:
    """pyodide(브라우저) 용 경량 finance 프리빌드.

    이미 빌드된 ``finance.parquet``(307MB) 에서 주요 계정 30 개(`LITE_ACCOUNTS`)
    × 5년치 분기만 추려 ``finance-lite.parquet``(~18MB) 를 생성한다.
    브라우저 pyodide 가 pyarrow 로 전체 로드 후 필터링에 사용한다.

    Parameters
    ----------
    sinceYear : int | None
        시작 연도. ``None`` 이면 `LITE_SINCE_YEAR` 기본값 사용.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 ``finance-lite.parquet`` 경로. 원본 없거나 결과 비면 None.

    Notes
    -----
    - `LITE_ACCOUNTS` 는 `scan/_helpers.py` 가 SSOT.
    - 원본 재빌드 없이 이미 정규화된 finance.parquet 에서 필터만 하므로 <1초.
    """
    from dartlab.providers.dart.finance.scanAccount import _buildFastKeys
    from dartlab.scan.parquetLoad import LITE_ACCOUNTS, LITE_SINCE_YEAR, LITE_SJ_DIVS

    effectiveSinceYear = LITE_SINCE_YEAR if sinceYear is None else sinceYear
    outDir = _scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outputPath = outDir / "finance-lite.parquet"
    srcPath = outDir / "finance.parquet"

    if not srcPath.exists():
        if verbose:
            _say("[finance-lite] finance.parquet 없음 → buildFinance 먼저 실행 필요")
        return None

    # 30개 snakeId → 원본 account_id/account_nm synonym union
    allKeys: set[str] = set()
    for sid in LITE_ACCOUNTS:
        allKeys.update(_buildFastKeys(sid))
    keysList = list(allKeys)

    if verbose:
        _say(f"[finance-lite] {len(LITE_ACCOUNTS)}계정 → {len(keysList)}키, sinceYear={effectiveSinceYear}")

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

    df = (
        pl.scan_parquet(str(srcPath))
        .filter(pl.col("sj_div").is_in(list(LITE_SJ_DIVS)))
        .filter(pl.col("bsns_year").cast(pl.Int32, strict=False) >= effectiveSinceYear)
        .filter(pl.col("account_id").is_in(keysList) | pl.col("account_nm").is_in(keysList))
        .select(keepCols)
        .collect()
    )

    if df.is_empty():
        if verbose:
            _say("[finance-lite] 결과 없음")
        return None

    df.write_parquet(str(outputPath), compression="zstd")

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    stocks = df["stockCode"].n_unique()
    if verbose:
        _say(f"[finance-lite] 완료: {stocks}종목, {df.height:,}행, {diskMb:.1f}MB, {elapsed:.1f}초 → {outputPath.name}")

    return outputPath


def buildValuation(*, verbose: bool = True) -> Path | None:
    """네이버 API 로 전종목 시세·밸류에이션 raw 수집 → ``valuation.parquet``.

    GH Actions cron (`valuationSnapshot.yml`, 매일 KST 04:00) 에서 호출. 결과 parquet 은
    HuggingFace ``eddmpython/dartlab-data`` 의 ``dart/scan/`` 에 업로드되며, 사용자는
    `dartlab.scan("valuation")` 호출 시 자동 다운로드 + 즉시 로드한다 (1초 이내).

    Returns
    -------
    Path | None
        생성된 `valuation.parquet` 경로. 수집 실패 또는 rate-limit 으로 0건이면
        기존 parquet 덮어쓰지 않고 ``None`` 반환.
    """
    from dartlab.scan.valuation import _RAW_SCHEMA, fetchValuationRaw

    if verbose:
        _say("[valuation] 상장사 목록 로드...")

    try:
        from dartlab.gather.listing import getKindList

        listing = getKindList()
    except (ImportError, OSError, RuntimeError) as e:
        if verbose:
            _say(f"[valuation] listing 로드 실패: {e}")
        return None

    if listing is None or listing.is_empty() or "종목코드" not in listing.columns:
        if verbose:
            _say("[valuation] 상장사 목록 없음")
        return None

    codes = listing["종목코드"].to_list()
    if verbose:
        _say(f"[valuation] {len(codes)}종목 네이버 API 수집 시작")

    t0 = time.perf_counter()
    raw = fetchValuationRaw(codes, verbose=verbose)
    elapsed = time.perf_counter() - t0

    if raw.is_empty():
        if verbose:
            _say(f"[valuation] 수집 0건 (rate-limit 의심, {elapsed:.1f}s) — 기존 parquet 유지")
        return None

    # 품질 게이트: 최소 55% 이상 수집됐을 때만 덮어쓰기
    coverage = raw.height / max(len(codes), 1)
    if coverage < 0.55:
        if verbose:
            _say(f"[valuation] 수집 {raw.height}/{len(codes)} ({coverage:.0%}) — 55% 미만, 기존 parquet 유지")
        return None

    outDir = _scanDir()
    outDir.mkdir(parents=True, exist_ok=True)
    outPath = outDir / "valuation.parquet"
    # 원본 네이버 raw (stockCode/marketCap/per/pbr/dividendYield/current/snapshotAt)
    # PSR/grade 는 loader 에서 매출 parquet 결합 후 runtime 계산.
    raw.select(list(_RAW_SCHEMA.keys())).write_parquet(str(outPath), compression="zstd")

    if verbose:
        sizeMb = outPath.stat().st_size / 1024 / 1024
        _say(f"[valuation] 완료: {raw.height}종목, {sizeMb:.1f}MB, {elapsed:.1f}s → {outPath}")
    return outPath


def buildScan(*, sinceYear: int = 2021, verbose: bool = True) -> dict[str, Path | list[Path] | None]:
    """changes + finance + finance-lite + report + sharesOutstanding 전체 프리빌드.

    Parameters
    ----------
    sinceYear : int
        시작 연도 (`buildFinance` 용). `buildFinanceLite` 는 `LITE_SINCE_YEAR` 기본값 사용.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    dict[str, Path | list[Path] | None]
        changes : Path | None — changes.parquet 경로
        finance : Path | None — finance.parquet 경로
        finance_lite : Path | None — finance-lite.parquet 경로 (pyodide 용 경량)
        report : list[Path] — apiType별 parquet 경로 목록
        sharesOutstanding : Path | None — sharesOutstanding.parquet 경로
    """
    if verbose:
        _say(f"전종목 scan 프리빌드 시작 (sinceYear={sinceYear})")
        _say("=" * 60)

    results: dict[str, Path | list[Path] | None] = {}

    results["changes"] = buildChanges(sinceYear=sinceYear, verbose=verbose)
    results["finance"] = buildFinance(sinceYear=sinceYear, verbose=verbose)
    # finance-lite 는 finance.parquet 직후에 파생 (재빌드 아니라 필터만)
    results["finance_lite"] = buildFinanceLite(verbose=verbose)
    results["report"] = buildReport(sinceYear=sinceYear, verbose=verbose)
    results["sharesOutstanding"] = _buildSharesOutstandingSafe(verbose=verbose)

    if verbose:
        _say("=" * 60)
        scanDir = _scanDir()
        if scanDir.exists():
            totalMb = sum(f.stat().st_size for f in scanDir.rglob("*.parquet")) / 1024 / 1024
            _say(f"scan 전체: {totalMb:.1f}MB")

    return results
