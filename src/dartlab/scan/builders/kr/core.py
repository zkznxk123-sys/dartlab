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
    """종목코드 → 결산월(int) SSOT 매핑 — 전종목 cover.

    데이터 소스 우선순위 (12월 결산도 12 로 명시 포함):

    1. DART corp_profile prefetch (``data/dart/scan/corpProfile.parquet``) —
       OpenDART ``companyInfo()`` 의 ``acc_mt`` 권위 SSOT (Phase 3, P-S11)
    2. listing (KIND) ``결산월`` 컬럼 — 상장사 보조 SSOT
    3. raw finance parquet 의 사업보고서 (``reprt_code='11011'``) ``rcept_no``
       첫 8자 (접수일자) → 접수월 - 3 (mod 12) = 결산월. 1·2 미포함 종목 보강.
    4. fallback: 12 (12월 결산 보수 가정 — 가장 흔한 케이스)

    Returns
    -------
    dict[str, int]
        {종목코드: 결산월 1-12} — 모든 finance 파일 종목에 결산월 부여. 12월 결산
        포함 (변환 함수에서 identity 매핑되어 안전). 빈 dict 이면 데이터 없음.

    Examples
    --------
    >>> fm = _fiscalMonthMap()
    >>> fm["005930"]   # 삼성전자 (12월 결산)
    12
    >>> fm["448730"]   # 삼성FN리츠 (10월 결산, listing 누락→raw 추정 또는 prefetch)
    10
    """
    result: dict[str, int] = {}

    # 1. DART corp_profile prefetch (권위 SSOT)
    result.update(_loadCorpProfileMap())

    # 2. listing 기반 (12월 포함 모든 결산월)
    try:
        from dartlab.gather.krx.listing import getKindList

        li = getKindList()
        if li is not None and not li.is_empty():
            if "결산월" in li.columns and "종목코드" in li.columns:
                for row in li.select(["종목코드", "결산월"]).iter_rows():
                    code, month_str = row
                    if code in result or not isinstance(month_str, str):
                        continue
                    try:
                        m = int(month_str.replace("월", ""))
                    except (ValueError, AttributeError):
                        continue
                    if 1 <= m <= 12:
                        result[code] = m
    except (ImportError, FileNotFoundError, OSError):
        pass

    # 3. raw 사업보고서 접수일 기반 — listing 미포함 종목 보강
    finDir = _financeDir()
    if finDir.exists():
        for pf in finDir.glob("*.parquet"):
            code = pf.stem
            if code in result:
                continue
            estimated = _estimateFiscalMonthFromAnnualFiling(pf)
            result[code] = estimated if estimated is not None else 12

    return result


def _loadCorpProfileMap() -> dict[str, int]:
    """corpProfile.parquet → stockCode → acc_mt 매핑 (권위 SSOT, Phase 3).

    DART OpenAPI ``companyInfo()`` 의 ``acc_mt`` (결산월) 를 prefetch 한 정적
    dataset. ``scripts/build/buildCorpProfile.py`` 가 corp_code 전체 list 를
    돌며 API 호출 후 ``data/dart/scan/corpProfile.parquet`` 으로 저장한다.

    Returns
    -------
    dict[str, int]
        {stockCode: 결산월 1-12}. 파일 없거나 파싱 실패 시 빈 dict.

    Notes
    -----
    - corpProfile.parquet 컬럼 스키마: ``corp_code`` · ``stockCode`` ·
      ``corp_name`` · ``acc_mt``.
    - ``stockCode`` 가 빈 문자열 (비상장 corp_code 일부) 인 row 는 제외.
    """
    from dartlab.reference.dataLoader import _dataDir

    profilePath = Path(_dataDir("scan")) / "corpProfile.parquet"
    if not profilePath.exists():
        return {}

    try:
        df = pl.scan_parquet(str(profilePath)).select(["stockCode", "acc_mt"]).collect(engine="streaming")
    except (pl.exceptions.PolarsError, OSError):
        return {}

    result: dict[str, int] = {}
    for row in df.iter_rows(named=True):
        code = row.get("stockCode")
        accMt = row.get("acc_mt")
        if not code or not accMt:
            continue
        try:
            m = int(str(accMt).replace("월", "").strip())
        except (ValueError, AttributeError):
            continue
        if 1 <= m <= 12:
            result[code] = m
    return result


def _estimateFiscalMonthFromAnnualFiling(pf: Path) -> int | None:
    """raw finance parquet → 사업보고서 접수일 기반 결산월 추정.

    DART 사업보고서 (``reprt_code='11011'``) 마감 = 결산월 종료 + 3개월 이내.
    ``rcept_no`` 첫 8자 = 접수일자 ``YYYYMMDD``. 결산월 = (접수월 - 3) mod 12.

    여러 사업보고서 접수일의 추정 결산월 **최빈값** 채택 (회계연도 변경 이력 노이즈
    방어).

    Parameters
    ----------
    pf : Path
        raw finance parquet 경로 (``{stockCode}.parquet``).

    Returns
    -------
    int | None
        추정 결산월 (1-12). 사업보고서 row 없거나 파싱 실패 시 None.
    """
    from collections import Counter

    try:
        lz = pl.scan_parquet(str(pf))
        schemaNames = lz.collect_schema().names()
        if "reprt_code" not in schemaNames or "rcept_no" not in schemaNames:
            return None
        annual = lz.filter(pl.col("reprt_code") == "11011").select("rcept_no").unique().collect(engine="streaming")
    except (pl.exceptions.PolarsError, OSError):
        return None

    if annual.is_empty():
        return None

    months: list[int] = []
    for rcn in annual["rcept_no"].to_list():
        if not isinstance(rcn, str) or len(rcn) < 8:
            continue
        try:
            rmonth = int(rcn[4:6])
        except ValueError:
            continue
        if not 1 <= rmonth <= 12:
            continue
        # 결산월 = 접수월 - 3, 1-12 cycling
        fm = ((rmonth - 3 - 1) % 12) + 1
        months.append(fm)

    if not months:
        return None
    return Counter(months).most_common(1)[0][0]


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
    endMonth = ((fiscalMonth + fiscalQ * 3 - 1) % 12) + 1
    calQ = ((endMonth - 1) // 3) + 1
    calYear = bsnsYear - 1 if endMonth > fiscalMonth else bsnsYear
    return calYear, calQ


_FISCAL_Q_MAP = {"1분기": 1, "2분기": 2, "3분기": 3, "4분기": 4}


def _calendarizeFiscalColumns(df: pl.DataFrame, fiscalMonth: int) -> pl.DataFrame:
    """``bsns_year`` / ``reprt_nm`` 을 캘린더 기준으로 환원 (polars 벡터).

    DART 사업연도/회계분기 → ``_toCalendarPeriod`` 동일 수학을 polars expression
    으로 옮긴 벡터 변환. 12월 결산은 identity (calYear=bsns_year, calQ=fiscalQ).

    Parameters
    ----------
    df : pl.DataFrame
        ``bsns_year`` (str/int) · ``reprt_nm`` (str, "N분기") 컬럼을 가진 raw finance.
    fiscalMonth : int
        결산월 (1-12).

    Returns
    -------
    pl.DataFrame
        ``bsns_year`` · ``reprt_nm`` 이 캘린더 기준으로 환원된 동일 schema DataFrame.
        ``reprt_nm`` 이 ``"N분기"`` 패턴이 아닌 row 는 그대로 보존.
    """
    bsnsInt = pl.col("bsns_year").cast(pl.Int32, strict=False)
    fq = pl.col("reprt_nm").replace_strict(_FISCAL_Q_MAP, default=None, return_dtype=pl.Int32)
    endMonth = ((fiscalMonth + fq * 3 - 1) % 12) + 1
    calQ = ((endMonth - 1) // 3) + 1
    calYear = pl.when(endMonth > fiscalMonth).then(bsnsInt - 1).otherwise(bsnsInt)
    # fq 가 null 이면 변환 skip (원본 유지)
    newBsns = (
        pl.when(fq.is_not_null() & bsnsInt.is_not_null()).then(calYear.cast(pl.Utf8)).otherwise(pl.col("bsns_year"))
    )
    newRept = (
        pl.when(fq.is_not_null() & bsnsInt.is_not_null())
        .then(calQ.cast(pl.Utf8) + pl.lit("분기"))
        .otherwise(pl.col("reprt_nm"))
    )
    return df.with_columns(newBsns.alias("bsns_year"), newRept.alias("reprt_nm"))


def _scanDir() -> Path:
    """scan 출력 디렉토리."""
    from dartlab.reference.dataLoader import _dataDir

    return Path(_dataDir("scan"))


def _docsDir() -> Path:
    from dartlab.reference.dataLoader import _dataDir

    return Path(_dataDir("docs"))


def _financeDir() -> Path:
    from dartlab.reference.dataLoader import _dataDir

    return Path(_dataDir("finance"))


def _reportDir() -> Path:
    from dartlab.reference.dataLoader import _dataDir

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

    lazyParts = [pl.scan_parquet(str(f)) for f in batchFiles]
    merged = pl.concat(lazyParts, how=how)
    merged.sink_parquet(str(outputPath), compression="zstd")
    return pl.scan_parquet(str(outputPath)).select(pl.len()).collect().item()


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
            pl.col("year")
            .shift(1)
            .over(["section_order", "section_title"])
            .alias("_prevYear"),  # polars-streaming-unsupported: over
            pl.col("section_content")
            .shift(1)
            .over(["section_order", "section_title"])
            .alias("_prevContent"),  # polars-streaming-unsupported: over
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
    """docs/*.parquet → ``changes.parquet`` 프리빌드 (전종목 sectionTitle 변화 감지).

    Parameters
    ----------
    sinceYear : int
        시작 연도. 이전 연도는 비교 baseline 으로만 사용. 기본 2021.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 ``changes.parquet`` 경로. docs 데이터 없으면 None.

    Raises
    ------
    polars.PolarsError
        docs parquet 손상 시.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.core import buildChanges
    >>> p = buildChanges(sinceYear=2021, verbose=True)
    >>> p.exists() if p else "no docs"

    Capabilities:
        - 전종목 docs (사업보고서 섹션) 의 연도별 변화 (appeared/disappeared/numeric/structural/wording)
          를 한 parquet 으로 합산. ``_buildRawChanges`` 가 종목당 변화 추출, 200 종목 배치로
          임시 청크 저장 후 ``_mergeBatchFiles`` 단일 파일 머지.

    AIContext:
        AI agent 가 ``dartlab.scan("disclosureRisk")`` 또는 ``dartlab.scan("dividendTrend")``
        호출 시 본 빌드 산출물을 LazyFrame 으로 스캔해 우발부채/감사 변경/사업 전환 같은
        선행 리스크 신호를 추출한다.

    Guide:
        - CI prebuild 파이프라인 (``.github/scripts/prebuildData.py``) 이 매일 2 회 자동 호출.
        - 로컬에서는 docs raw parquet 가 ``data/dart/docs/`` 에 있을 때만 의미.
        - 결과 parquet (~수십 MB) 은 HF ``eddmpython/dartlab-data`` 의 ``dart/scan/`` 에 업로드.

    When:
        Data Sync 직후 (KST 03:00 / 15:00) prebuild 단계에서. 사용자가 직접 호출하는 일은 드물다 —
        스캔 axis (disclosureRisk/dividendTrend) 호출이 자동 다운로드를 트리거하므로.

    How:
        ``buildScan`` 의 첫 단계. ``_docsDir()`` 의 종목별 raw parquet 을 순회 → 종목당
        ``_buildRawChanges`` 호출 → 200 단위 배치 임시 청크 → 전체 ``_mergeBatchFiles`` 단일 합산.
        실패 종목은 silent skip + ``verbose=True`` 에서만 카운트 표시.

    Requires:
        - 로컬 ``data/dart/docs/{stockCode}.parquet`` (Data Sync 가 채움)
        - ``year`` · ``section_order`` · ``section_title`` · ``section_content`` 컬럼

    SeeAlso:
        - :func:`buildScan` — 본 함수를 포함한 전체 프리빌드 통합 호출
        - :func:`_buildRawChanges` — 종목당 변화 추출 (private)
        - :func:`buildFinance` · :func:`buildReport` — 같은 prebuild 단계의 동료 빌더
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

    # parents[3] = src/dartlab (scan/builders/kr/core.py → 3 단계 up)
    mapPath = Path(__file__).resolve().parents[3] / "core" / "data" / "accountMappings.json"
    if not mapPath.exists():
        return {}
    try:
        data = json.loads(mapPath.read_text(encoding="utf-8"))
        return data.get("mappings", {})
    except (json.JSONDecodeError, OSError):
        return {}


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
    >>> from dartlab.scan.builders.kr.core import buildFinance
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
        - :func:`buildFinanceLite` — 본 빌드 산출물을 필터해 pyodide 경량본 파생
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

    # 계정명 정규화 매핑 로드
    acctMap = _loadAccountMap()
    if verbose and acctMap:
        _say(f"[finance] accountMappings: {len(acctMap)}개 매핑 로드")

    # 결산월 SSOT — 전종목 (12월 결산 포함). 변환 분기에서 일관 적용 (12월은 identity).
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

        # 모든 종목 캘린더 분기 환원 (12월 결산 = identity). polars 벡터 변환.
        code = pf.stem
        fm = fmMap.get(code, 12)
        if "bsns_year" in df.columns and "reprt_nm" in df.columns:
            df = _calendarizeFiscalColumns(df, fm)

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
    from datetime import date

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


# ── report ───────────────────────────────────────────────────────────


def buildReport(*, sinceYear: int = 2021, verbose: bool = True) -> list[Path]:
    """report/*.parquet → apiType별 12개 분리 parquet 프리빌드.

    ``SCAN_API_TYPES`` 12 종 (majorHolder/executive/employee/auditOpinion/dividend/...) 의
    각 apiType 마다 종목별 raw row 를 모아 별도 parquet 으로 출력. report.parquet 단일
    합본이 아닌 12개 분할 — apiType 마다 스키마가 다르고 사용 단위가 다르므로.

    Parameters
    ----------
    sinceYear : int
        포함할 최소 ``year`` (``year >= sinceYear``). 기본 2021.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    list[Path]
        생성된 apiType별 parquet 경로 목록. data 없는 apiType 은 제외.

    Raises
    ------
    polars.PolarsError
        report parquet 손상 또는 ``sink_parquet`` 실패 시.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.core import buildReport
    >>> paths = buildReport(sinceYear=2021, verbose=True)
    >>> [p.name for p in paths[:3]]

    Capabilities:
        - 종목별 raw report parquet 을 12 apiType 별로 split. ``apiType`` 컬럼 == 카테고리
          매칭으로 종목 row 를 해당 apiType bucket 에 추가. 200 종목 단위 배치 청크 → merge.
        - apiType 마다 다른 컬럼 스키마 흡수 (``diagonal_relaxed`` concat).

    AIContext:
        ``scan("governance")`` (executive/majorHolder/outsideDirector), ``scan("workforce")``
        (employee/executivePay*), ``scan("capital")`` (dividend/treasuryStock/capitalChange/
        corporateBond), ``scan("audit")`` (auditOpinion/minorityHolder) 등 비재무 scan 축의
        1 차 source. AI 가 axis 호출 시 본 빌드 산출물을 LazyFrame 으로 필터한다.

    Guide:
        - 출력 경로: ``data/dart/scan/report/{apiType}.parquet``
        - 12 apiType 중 일부만 raw 에 있으면 그 apiType 만 생성 (나머지 silent skip).
        - 파일 크기는 apiType 마다 차이 큰 — employee/executive 가 가장 크다.

    When:
        매 prebuild 사이클 (KST 03:00 / 15:00). buildChanges/buildFinance 직후.
        사용자 직접 호출 드물다.

    How:
        ``buildScan`` 의 4 번째 단계. apiType 별 buffer dict (``apiChunks``) 를 유지하면서
        종목당 raw 를 12 apiType 으로 filter → buffer push. ``_BATCH`` (200) 도달 시 임시
        청크 flush. 종료 시 잔존 청크 flush + apiType 마다 ``_mergeBatchFiles`` 단일 파일 머지.
        12 임시 디렉토리 (``_tmp_{apiType}/``) 사용 후 cleanup.

    Requires:
        - 로컬 ``data/dart/report/{stockCode}.parquet`` (Data Sync 가 채움)
        - ``apiType`` 컬럼 (필수, 없으면 종목 skip)

    SeeAlso:
        - :data:`SCAN_API_TYPES` — 처리 대상 12 apiType list
        - :func:`buildScan` — 본 함수 포함 통합 호출
        - :func:`buildChanges` · :func:`buildFinance` — 같은 prebuild 단계 동료 빌더
        - :mod:`dartlab.scan.io.parquet` — :func:`scanParquets` 가 본 빌드 출력 lazy scan
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
        from dartlab.providers.dart.docs.finance.shareCapital import buildSharesOutstandingScan

        if verbose:
            _say("[shares] 발행주식수 풀 빌드 시작")
        df = buildSharesOutstandingScan()
        if verbose:
            _say(f"[shares] 완료: rows={df.height} stocks={df['stockCode'].n_unique()}")
        return _scanDir() / "sharesOutstanding.parquet"
    except (FileNotFoundError, RuntimeError, OSError, ValueError) as exc:
        if verbose:
            _say(f"[shares] 실패: {exc}")
        return None


def buildFinanceLite(*, sinceYear: int | None = None, verbose: bool = True) -> Path | None:
    """pyodide(브라우저) 용 ``finance-lite.parquet`` 파생 — finance.parquet 30 계정 5년 필터.

    이미 빌드된 ``finance.parquet`` (~307MB) 에서 주요 계정 30 개 (``LITE_ACCOUNTS``)
    × 5년치 분기만 추려 ``finance-lite.parquet`` (~18MB) 를 생성한다. 브라우저 pyodide
    환경이 ``pl.scan_parquet`` 미지원이라 pyarrow 로 전체 로드 후 ``pl.from_arrow`` 변환해
    쓰는데, 원본 307MB 는 메모리 한계라 경량본이 필수.

    Parameters
    ----------
    sinceYear : int | None
        포함할 최소 ``bsns_year``. ``None`` 이면 ``LITE_SINCE_YEAR`` 기본 (2022) 사용.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    Path | None
        생성된 ``finance-lite.parquet`` 경로. 원본 ``finance.parquet`` 없거나 결과 비면 None.

    Raises
    ------
    polars.PolarsError
        원본 ``finance.parquet`` 손상 또는 ``sink_parquet`` 실패 시.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.core import buildFinanceLite
    >>> p = buildFinanceLite(verbose=True)
    >>> p.stat().st_size < 25_000_000 if p else "no source"
    True

    Capabilities:
        - 원본 합본 ``finance.parquet`` 에 (1) ``sj_div ∈ LITE_SJ_DIVS`` (IS/BS/CIS/CF — SCE 제외)
          (2) ``bsns_year >= sinceYear`` (3) ``account_id/account_nm ∈ LITE_ACCOUNTS synonym union``
          필터 push-down → ``sink_parquet``. lazy 라 메모리 부담 거의 없음 (<1초, MB 단위).
        - ``_buildFastKeys`` 가 30 개 snakeId 마다 한/영 변형 컬렉션 (~수백 키) 으로 확장.

    AIContext:
        Pyodide 빌드 (``dartlab.io/pyodide``) 의 ``dartlab.scan("account", ...)`` 호출이
        ``finance.parquet`` 대신 본 경량본을 로드. 브라우저 메모리 한계 안에서 30 핵심 계정
        시계열을 사용 가능하게 만든다.

    Guide:
        - 빌드 순서: ``buildFinance`` 직후 (원본이 이미 캘린더 환원·snakeId 정규화 상태).
        - 새 계정 필요 시 ``LITE_ACCOUNTS`` 에만 추가하면 자동 반영. 30 개 한도는 메모리 정책.
        - 5 년치 (2022~) 분기 보장. 더 긴 시계열은 별도 풀빌드 호출.

    When:
        매 prebuild 사이클 (``buildScan`` 의 3 번째 단계). pyodide 배포가 본 빌드 산출물을
        HF 에서 자동 다운로드해 브라우저 ``scan`` 호출에 활용.

    How:
        ``finance.parquet`` 의 lazy scan → 3 단 filter chain → ``sink_parquet``. summary
        쿼리 (rows / unique stocks) 로 결과 검증. 0 행이면 출력 unlink + None 반환.
        coverage 게이트 없음 (재빌드 호출이라 원본 기준).

    Requires:
        - 선행 ``buildFinance`` 산출 ``finance.parquet`` (``data/dart/scan/finance.parquet``)
        - ``LITE_ACCOUNTS`` · ``LITE_SJ_DIVS`` · ``LITE_SINCE_YEAR`` (``scan/io/parquet.py`` SSOT)
        - ``_buildFastKeys`` (한/영 라벨 union — ``providers/dart/finance/scanAccount.py``)

    SeeAlso:
        - :func:`buildFinance` — 본 빌드의 source 합본 생성
        - :data:`LITE_ACCOUNTS` · :data:`LITE_SJ_DIVS` · :data:`LITE_SINCE_YEAR`
        - :func:`buildScan` — 본 함수를 포함한 통합 호출
    """
    from dartlab.providers.dart.finance.scanAccount import _buildFastKeys
    from dartlab.scan.io.parquet import LITE_ACCOUNTS, LITE_SINCE_YEAR, LITE_SJ_DIVS

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
            _say("[finance-lite] 결과 없음")
        return None

    elapsed = time.perf_counter() - t0
    diskMb = outputPath.stat().st_size / 1024 / 1024
    stocks = int(summary["stocks"][0])
    if verbose:
        _say(f"[finance-lite] 완료: {stocks}종목, {rows:,}행, {diskMb:.1f}MB, {elapsed:.1f}초 → {outputPath.name}")

    return outputPath


def buildValuation(*, verbose: bool = True) -> Path | None:
    """네이버 API 로 전종목 시세·밸류에이션 raw 수집 → ``valuation.parquet``.

    GH Actions cron (``valuationSnapshot.yml``, 매일 KST 04:00) 에서 호출. 결과 parquet 은
    HuggingFace ``eddmpython/dartlab-data`` 의 ``dart/scan/`` 에 업로드되며, 사용자는
    ``dartlab.scan("valuation")`` 호출 시 자동 다운로드 + 즉시 로드한다 (1초 이내).

    Parameters
    ----------
    verbose : bool, default True
        진행 라인을 ``logger.info`` 로 출력.

    Returns
    -------
    Path | None
        생성된 ``valuation.parquet`` 경로. 수집 실패 또는 rate-limit 으로 0 건이거나
        coverage < 55 % 이면 기존 parquet 덮어쓰지 않고 ``None`` 반환.

    Raises
    ------
    없음 — listing 로드 실패 · 네이버 rate-limit · OSError 는 내부에서 흡수 + None 반환.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.core import buildValuation
    >>> p = buildValuation(verbose=True)
    >>> p.name if p else "rate-limited"
    'valuation.parquet'

    Capabilities:
        - 상장사 ~3964 종목의 ``marketCap`` · ``per`` · ``pbr`` · ``dividendYield`` · ``current``
          · ``snapshotAt`` 6 컬럼을 네이버 API 에서 raw 수집. PSR/grade 는 loader 가 매출 parquet
          결합 후 runtime 계산 — 본 빌드는 raw 만 책임.
        - 품질 게이트 — 수집 coverage < 55 % 이면 기존 parquet 보존 (stale data > corrupted).

    AIContext:
        ``dartlab.scan("valuation")`` 호출의 1 차 source. AI 가 밸류에이션 비교 시 (PER/PBR/PSR)
        본 빌드 산출물 + finance 매출 결합한 결과를 사용. snapshotAt 컬럼이 데이터 freshness 의
        ground truth — 24 h 초과 시 사용자에게 stale 경고.

    Guide:
        - cron 외 수동 호출: rate-limit 위험 — 같은 IP 가 짧은 시간에 두 번 돌리면 0 건 응답.
        - 출력 ``valuation.parquet`` 는 ``HF eddmpython/dartlab-data`` 의 ``dart/scan/`` 동기화.
        - listing 미보유 환경에서는 silent skip (None).

    When:
        GH Actions cron 매일 KST 04:00 자동 호출. 로컬 수동 호출은 디버깅/품질 검증 한정.

    How:
        listing (KRX KIND) → 종목코드 리스트 → ``fetchValuationRaw`` (네이버 API 병렬) →
        coverage 게이트 → ``_RAW_SCHEMA`` 컬럼만 selecting → 단일 parquet write. rate-limit
        대응은 ``fetchValuationRaw`` 내부 backoff 가 담당.

    Requires:
        - 네이버 finance API 접근 (rate-limit 의식)
        - ``dartlab.gather.krx.listing.getKindList()`` 가 종목코드 반환
        - ``dartlab.scan.financial.valuation`` 의 ``fetchValuationRaw`` · ``_RAW_SCHEMA``

    SeeAlso:
        - :func:`dartlab.scan.financial.valuation.fetchValuationRaw` — 네이버 raw 수집
        - :func:`dartlab.scan.io.parquet.loadValuationSnapshot` — 빌드 결과 lazy load
        - :func:`buildScan` — 본 함수는 통합 빌드에 포함되지 않음 (별도 cron)
    """
    from dartlab.scan.financial.valuation import _RAW_SCHEMA, fetchValuationRaw

    if verbose:
        _say("[valuation] 상장사 목록 로드...")

    try:
        from dartlab.gather.krx.listing import getKindList

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
    """scan 프리빌드 통합 (changes + finance + finance-lite + report + sharesOutstanding).

    ``.github/scripts/prebuildData.py`` 가 매 prebuild 사이클 (KST 03:00 / 15:00) 에 호출하는
    파사드. 하위 5 단계를 순서대로 실행하며, 각 단계 실패는 silent skip — 한 단계가 깨져도
    다른 산출물은 정상 생성. ``buildValuation`` 은 별도 cron 이므로 본 함수에 포함 안 됨.

    Parameters
    ----------
    sinceYear : int
        시작 연도 (``buildFinance`` / ``buildReport`` / ``buildChanges`` 공통). 기본 2021.
        ``buildFinanceLite`` 는 ``LITE_SINCE_YEAR`` 자체 기본값 (2022) 사용.
    verbose : bool
        진행 로그 출력 여부.

    Returns
    -------
    dict[str, Path | list[Path] | None]
        - changes : Path | None — ``changes.parquet`` 경로
        - finance : Path | None — ``finance.parquet`` 경로
        - finance_lite : Path | None — ``finance-lite.parquet`` 경로 (pyodide 경량본)
        - report : list[Path] — apiType별 parquet 경로 목록
        - sharesOutstanding : Path | None — ``sharesOutstanding.parquet`` 경로

    Raises
    ------
    polars.PolarsError
        하위 ``buildChanges`` · ``buildFinance`` · ``buildReport`` 가 발생시키는 예외 전파.
        ``_buildSharesOutstandingSafe`` 는 자체 catch 라 전파 안 됨.

    Examples
    --------
    >>> from dartlab.scan.builders.kr.core import buildScan
    >>> result = buildScan(sinceYear=2021, verbose=True)
    >>> result["finance"].exists() if result["finance"] else "no data"
    True

    Capabilities:
        - 5 산출물 (changes / finance / finance-lite / report 12 / sharesOutstanding) 의
          단일 호출 파사드. 호출자는 본 함수 1 회로 모든 prebuild 출력을 얻는다.
        - 단계 간 의존: finance-lite ← finance (재빌드 아닌 필터만). 다른 단계는 독립.

    AIContext:
        prebuild 파이프라인의 main entry. AI 가 "scan 프리빌드 어떻게 만들지?" 질문 시 본
        함수 호출만 알려주면 충분 (하위 5 함수는 implementation detail).

    Guide:
        - 호출 직전에 ``scripts/build/buildCorpProfile.py`` 실행 권장 (결산월 SSOT 최신화).
        - 실행 후 산출 합계 (MB) 로깅. HF 업로드는 호출자 (``prebuildData.py``) 책임.
        - 단계 1 개 실패해도 다른 4 개는 정상 — 부분 산출 허용 (CI 회복력).

    When:
        매 prebuild 사이클 — Data Sync workflow 직후 KST 03:00 / 15:00. 로컬 수동 실행은
        raw 데이터 충분히 갖춘 환경에서 디버깅 / 검증 용도.

    How:
        1) ``buildChanges`` → 2) ``buildFinance`` (결산월 환원 + sanity check 자동) →
        3) ``buildFinanceLite`` (finance.parquet 직후 파생) → 4) ``buildReport`` (apiType 분할)
        → 5) ``_buildSharesOutstandingSafe`` (별도 try/except wrapper).

    Requires:
        - 로컬 ``data/dart/{docs,finance,report}/{stockCode}.parquet`` (Data Sync 결과)
        - 출력 디렉토리 쓰기 권한 (``data/dart/scan/``)

    SeeAlso:
        - :func:`buildChanges` · :func:`buildFinance` · :func:`buildFinanceLite` ·
          :func:`buildReport` · :func:`_buildSharesOutstandingSafe`
        - :func:`buildValuation` — 본 함수에 포함 안 됨 (별도 cron 트리거)
        - ``.github/scripts/prebuildData.py`` — 호출자 + HF 업로드 + 품질 검증
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
