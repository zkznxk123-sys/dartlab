"""scan 공용 유틸리티 — report parquet 스캔, 숫자 파싱, listing 로드."""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

import polars as pl

# ── 계정 라벨 SSOT (scan 모듈 공용) ──
# 같은 회계 개념의 snake_id / 표시명 변형을 한 곳에 통합.
# 신규 변형 발견 시 여기서만 추가 → scan/{efficiency,growth,profitability,valuation} 자동 반영.

REVENUE_IDS = {"Revenue", "revenue", "ifrs-full_Revenue", "dart_Revenue"}
REVENUE_NMS = {"매출액", "수익(매출액)", "영업수익"}

OP_IDS = {
    "ProfitLossFromOperatingActivities",
    "operatingIncome",
    "ifrs-full_ProfitLossFromOperatingActivities",
    "dart_OperatingIncomeLoss",
}
OP_NMS = {"영업이익", "영업이익(손실)"}

NI_IDS = {
    "ProfitLoss",
    "netIncome",
    "ifrs-full_ProfitLoss",
    "dart_ProfitLoss",
    "ProfitLossAttributableToOwnersOfParent",
}
NI_NMS = {"당기순이익", "당기순이익(손실)"}

TA_IDS = {"Assets", "totalAssets", "ifrs-full_Assets", "dart_Assets"}
TA_NMS = {"자산총계", "자산 총계"}

_scanDownloaded = False

# scan 프리빌드 freshness — HF 수집 주기(일 1회)에 맞춰 24h TTL
_SCAN_FRESHNESS_TTL_SECONDS = 24 * 3600


# ── finance-lite 스펙 (pyodide/브라우저 용 경량 프리빌드) ──────────────
#
# 원본 `finance.parquet`(307MB) 을 아래 30 개 snakeId 로 필터하고 2022년부터만
# 남긴 경량본. 실측 18MB 수준. 브라우저 pyodide 에서 `pl.scan_parquet` 미지원이라
# pyarrow 로 전체 로드 → `pl.from_arrow` 로 변환해 쓴다.
#
# 선정 기준: scan 하위 모듈(profitability/growth/quality/liquidity/efficiency/
# cashflow/dividendTrend/capital/debt)과 analysis 엔진이 실사용하는 계정 union.
# 전부 sortOrder.json 에 등록된 정규 snakeId.

_LITE_ACCOUNTS_IS: tuple[str, ...] = (
    "sales",
    "cost_of_sales",
    "gross_profit",
    "operating_expenses",
    "operating_profit",
    "finance_income",
    "finance_costs",
    "profit_before_tax",
    "income_tax_expense",
    "net_income",
)
_LITE_ACCOUNTS_BS: tuple[str, ...] = (
    "cash_and_cash_equivalents",
    "current_assets",
    "inventories",
    "trade_receivables",
    "noncurrent_assets",
    "property_plant_and_equipment",
    "intangible_assets",
    "current_liabilities",
    "trade_payables",
    "noncurrent_liabilities",
    "total_stockholders_equity",
    "retained_earnings",
)
_LITE_ACCOUNTS_CF: tuple[str, ...] = (
    "operating_cashflow",
    "investing_cashflow",
    "financing_cashflow",
    "cash_and_cash_equivalents_at_the_end_of_year",
    "cash_and_cash_equivalents_beginning",
    "changes_in_operating_assets_and_liabilities",
    "depreciation",
    "net_increase_decrease_in_cash_and_cash_equivalents",
)
LITE_ACCOUNTS: tuple[str, ...] = _LITE_ACCOUNTS_IS + _LITE_ACCOUNTS_BS + _LITE_ACCOUNTS_CF

# lite 빌드에 포함할 재무제표 구분 (SCE 제외 — 용량 27.8% 차지, scan 미사용)
LITE_SJ_DIVS: tuple[str, ...] = ("IS", "BS", "CIS", "CF")

# lite 기본 시작 연도 (5년치 분기 보장: 2022Q1 ~ 최신)
LITE_SINCE_YEAR: int = 2022

# scan 프리빌드 루트 필수 파일 — HF `dart/scan/` 루트에 있어야 하는 산출물.
# 과거 `allow_patterns="dart/scan/**/*.parquet"` 버그로 루트 파일이 누락된
# 불완전 캐시 상태 환경이 존재한다 (report/ 12개만 받아진 상태). 이 리스트로
# 완전성을 검증해 한 개라도 없으면 재다운로드를 강제한다.
_REQUIRED_SCAN_ROOT_FILES: tuple[str, ...] = (
    "finance.parquet",
    "changes.parquet",
    "sharesOutstanding.parquet",
)


def _isScanComplete(scanDir: Path) -> bool:
    """scan 프리빌드 루트 필수 파일이 모두 존재하는지 확인."""
    return all((scanDir / name).exists() for name in _REQUIRED_SCAN_ROOT_FILES)


def _ensureScanData() -> Path:
    """scan 프리빌드 디렉토리 확인 — 없거나 오래됐으면 HF에서 자동 다운로드.

    일반 환경: 루트 필수 파일(finance/changes/sharesOutstanding) 이 모두 존재하고
    TTL(24h) 이내면 즉시 반환. 하나라도 없거나 TTL 초과면 다운로드 시도.

    Pyodide(브라우저): 경량본 `finance-lite.parquet` 1 개만 요구. 없으면 HF 에서
    개별 fetch (`_pyodideFetchScanLite` 경유).

    Returns
    -------
    Path
        scan 프리빌드 디렉토리 경로 (~/.dartlab/data/scan/).
    """
    from dartlab.core.dataLoader import _IS_PYODIDE, _dataDir
    from dartlab.core.messaging import emit

    scanDir = Path(_dataDir("scan"))

    global _scanDownloaded
    if _scanDownloaded:
        return scanDir

    # Pyodide: finance-lite.parquet 단일 파일만 체크 (전체 프리빌드는 용량상 불가)
    if _IS_PYODIDE:
        liteParquet = scanDir / "finance-lite.parquet"
        if liteParquet.exists():
            _scanDownloaded = True
            return scanDir
        emit("scan:prebuild_missing")
        try:
            from dartlab.core.dataLoader import downloadAll

            downloadAll("scan")  # pyodide 분기에서 _pyodideFetchScanLite 호출
            _scanDownloaded = True
            emit("scan:prebuild_ready", fileCount="finance-lite")
        except (ImportError, RuntimeError, OSError) as e:
            emit("scan:prebuild_failed", error=str(e))
        return scanDir

    if _isScanComplete(scanDir):
        financeParquet = scanDir / "finance.parquet"
        age = time.time() - financeParquet.stat().st_mtime
        if age < _SCAN_FRESHNESS_TTL_SECONDS:
            # 최신 — HF 호출 없이 즉시 반환
            _scanDownloaded = True
            return scanDir
        # TTL 초과 — 갱신 시도하되 실패해도 기존 파일 사용
        try:
            from dartlab.core.dataLoader import downloadAll

            downloadAll("scan")
        except (ImportError, RuntimeError, ValueError):
            pass
        _scanDownloaded = True
        return scanDir

    # 루트 필수 파일 누락 (신규 사용자 또는 과거 버그로 불완전 캐시) → HF 다운로드
    emit("scan:prebuild_missing")
    try:
        from dartlab.core.dataLoader import downloadAll

        downloadAll("scan")
        _scanDownloaded = True
        fileCount = sum(1 for _ in scanDir.rglob("*.parquet"))
        emit("scan:prebuild_ready", fileCount=fileCount)
    except (ImportError, RuntimeError, ValueError) as e:
        emit("scan:prebuild_failed", error=str(e))

    return scanDir


def scanParquets(apiType: str, keepCols: list[str]) -> pl.DataFrame:
    """report parquet에서 특정 apiType만 LazyFrame 스캔.

    scan/report/{apiType}.parquet 프리빌드가 있으면 단일 파일에서 즉시 로드.
    없으면 종목별 parquet 순회 (fallback).

    Parameters
    ----------
    api_type : str
        DART API 유형 (예: "majorHolder", "auditReport").
    keep_cols : list[str]
        추출할 컬럼 목록 (예: ["stockCode", "year", "지분율"]).

    Returns
    -------
    pl.DataFrame
        keep_cols 중 존재하는 컬럼만 포함한 전종목 결과.
        데이터 없으면 빈 DataFrame.
    """
    # 1순위: 프리빌드 scan parquet (없으면 자동 다운로드 시도)
    scanDir = _ensureScanData()
    scan_path = scanDir / "report" / f"{apiType}.parquet"
    if scan_path.exists():
        try:
            lf = pl.scan_parquet(str(scan_path))
            schema_names = lf.collect_schema().names()
            available = [c for c in keepCols if c in schema_names]
            non_meta = [c for c in available if c not in ("stockCode", "year", "quarter")]
            if non_meta:
                return lf.select(available).collect()
        except (pl.exceptions.PolarsError, OSError):
            pass  # fallback to per-file scan

    # 2순위: 종목별 순회 (fallback)
    from dartlab.core.dataLoader import _dataDir

    report_dir = Path(_dataDir("report"))
    parquet_files = sorted(report_dir.glob("*.parquet"))

    if not parquet_files:
        from dartlab.core.messaging import emit

        emit("hint:market_data_needed", category="report", fn=apiType)
        return pl.DataFrame()

    frames: list[pl.LazyFrame] = []
    for pf in parquet_files:
        try:
            lf = pl.scan_parquet(str(pf))
            schema_names = lf.collect_schema().names()
            if "apiType" not in schema_names:
                continue
            available = [c for c in keepCols if c in schema_names]
            non_meta = [c for c in available if c not in ("stockCode", "year", "quarter")]
            if not non_meta:
                continue
            lf = lf.filter(pl.col("apiType") == apiType).select(available)
            frames.append(lf)
        except (pl.exceptions.ComputeError, OSError):
            continue

    if not frames:
        return pl.DataFrame()

    all_cols: set[str] = set()
    for lf in frames:
        all_cols.update(lf.collect_schema().names())
    unified: list[pl.LazyFrame] = []
    for lf in frames:
        missing = all_cols - set(lf.collect_schema().names())
        if missing:
            lf = lf.with_columns([pl.lit(None).alias(c) for c in missing])
        unified.append(lf.select(sorted(all_cols)))

    return pl.concat(unified).collect()


from dartlab.core.utils.helpers import parseNumStr  # noqa: E402


def extractAccount(sub: pl.DataFrame, ids: set, nms: set, amtCol: str = "thstrm_amount") -> float | None:
    """DataFrame에서 account_id/account_nm 매칭 → 금액 추출.

    Parameters
    ----------
    sub : pl.DataFrame
        단일 종목의 재무 데이터.
    ids : set
        매칭할 account_id 집합.
    nms : set
        매칭할 account_nm 집합.
    amtCol : str
        금액 컬럼명 (기본 "thstrm_amount").

    Returns
    -------
    float | None
        첫 매칭 계정의 금액 (원). 매칭 없으면 None.
    """
    for row in sub.iter_rows(named=True):
        aid = row.get("account_id", "")
        anm = row.get("account_nm", "")
        if aid in ids or anm in nms:
            val = parseNumStr(row.get(amtCol))
            if val is not None:
                return val
    return None


def findLatestYear(raw: pl.DataFrame, checkCol: str, minCount: int = 500) -> str | None:
    """check_col에 유효 데이터가 min_count 이상인 가장 최근 연도 반환.

    Parameters
    ----------
    raw : pl.DataFrame
        year 컬럼을 포함한 전종목 데이터.
    check_col : str
        유효성 검사 대상 컬럼명.
    min_count : int
        해당 연도에 필요한 최소 유효 행 수.

    Returns
    -------
    str | None
        가장 최근 유효 연도 문자열 (예: "2024"). 없으면 None.
    """
    years_desc = sorted(raw["year"].unique().to_list(), reverse=True)
    for y in years_desc:
        sub = raw.filter(pl.col("year") == y)
        ok = sub.filter(pl.col(checkCol).is_not_null() & (pl.col(checkCol) != "-") & (pl.col(checkCol) != "")).shape[0]
        if ok >= minCount:
            return y
    return None


QUARTER_ORDER = {"2분기": 1, "4분기": 2, "3분기": 3, "1분기": 4}


def pickBestQuarter(df: pl.DataFrame) -> pl.DataFrame:
    """가장 선호하는 분기만 필터 (Q2 > Q4 > Q3 > Q1).

    Parameters
    ----------
    df : pl.DataFrame
        quarter 컬럼을 포함한 전종목 데이터.

    Returns
    -------
    pl.DataFrame
        가장 선호하는 분기 1개만 남긴 DataFrame.
    """
    quarters = df["quarter"].unique().to_list()
    best = sorted(quarters, key=lambda q: QUARTER_ORDER.get(q, 99))
    return df.filter(pl.col("quarter") == best[0]) if best else df


def loadListing():
    """상장사 목록 로드.

    Returns
    -------
    pl.DataFrame
        종목코드, 종목명, 업종 등 상장사 기본 정보.

    Notes
    -----
    network/scanner.py 의 load_listing 에 위임.
    """
    from dartlab.scan.network.scanner import loadListing as _ll

    return _ll()


def parseDateYear(s) -> int | None:
    """날짜 문자열에서 연도 추출.

    Parameters
    ----------
    s : str | None
        날짜 문자열 (예: "2021.06.15", "2021-06-15").

    Returns
    -------
    int | None
        연도 (예: 2021). 파싱 불가면 None.
    """
    if s is None:
        return None
    s = str(s).strip()
    if s in ("", "-"):
        return None
    for sep in (".", "-"):
        if sep in s:
            parts = s.split(sep)
            if parts:
                try:
                    y = int(parts[0])
                    if 1990 <= y <= 2030:
                        return y
                except ValueError:
                    pass
    return None


def filterLatestPerStock(target: pl.DataFrame, scCol: str = "stockCode", yearCol: str = "bsns_year") -> pl.DataFrame:
    """종목별 최신 ``bsns_year`` 행만 남긴다.

    scan 축이 ``target.filter(bsns_year == latestYear)`` 처럼 **글로벌 최신 연도** 로
    커트하면, 2026 Q1 조기 제출 3 종목 때문에 2025 자 2895 종목이 전부 버려지는 버그가
    발생 (2026-04-23 확인). 해당 버그는 13 개 축 파일에 분산 존재.

    올바른 패턴: 종목별 ``group_by`` 로 **각자 최신 연도** 선택.

    Parameters
    ----------
    target : pl.DataFrame
        scan 대상 (finance parquet filter 결과). 반드시 ``scCol`` · ``yearCol`` 컬럼 포함.
    scCol : str, default ``"stockCode"``
        종목코드 컬럼명.
    yearCol : str, default ``"bsns_year"``
        사업년도 컬럼명.

    Returns
    -------
    pl.DataFrame
        각 종목의 자기 최신 연도 행만 남긴 DataFrame.
    """
    if target.is_empty() or scCol not in target.columns or yearCol not in target.columns:
        return target
    latest = target.group_by(scCol).agg(pl.col(yearCol).max().alias("_maxYear"))
    return target.join(latest, on=scCol).filter(pl.col(yearCol) == pl.col("_maxYear")).drop("_maxYear")


def _scanFinanceFromMerged(
    scanPath: Path,
    sjDivs: list[str],
    accountIds: set[str],
    accountNms: set[str],
    amountCol: str,
) -> dict[str, float]:
    """합산 finance parquet에서 종목별 최신 연도 값 추출.

    Parameters
    ----------
    scanPath : Path
        프리빌드 finance.parquet 경로.
    sjDivs : list[str]
        재무제표 구분 코드 (예: ["IS", "CIS"]).
    accountIds : set[str]
        매칭할 account_id 집합.
    accountNms : set[str]
        매칭할 account_nm 집합.
    amountCol : str
        금액 컬럼명 (예: "thstrm_amount").

    Returns
    -------
    dict[str, float]
        {종목코드: 금액(원)} — 종목별 최신 연도 첫 매칭 계정의 값.
    """
    scCol = "stockCode" if "stockCode" in pl.scan_parquet(str(scanPath)).collect_schema().names() else "stock_code"

    target = (
        pl.scan_parquet(str(scanPath))
        .filter(
            pl.col("sj_div").is_in(sjDivs)
            & (pl.col("fs_nm").str.contains("연결") | pl.col("fs_nm").str.contains("재무제표"))
        )
        .collect()
    )

    if target.is_empty() or "account_id" not in target.columns:
        return {}

    # 연결 우선
    cfs = target.filter(pl.col("fs_nm").str.contains("연결"))
    target = cfs if not cfs.is_empty() else target

    # 종목별 최신 연도만
    latestYear = target.group_by(scCol).agg(pl.col("bsns_year").max().alias("_maxYear"))
    target = target.join(latestYear, on=scCol).filter(pl.col("bsns_year") == pl.col("_maxYear")).drop("_maxYear")

    # 계정 매칭
    matched = target.filter(pl.col("account_id").is_in(list(accountIds)) | pl.col("account_nm").is_in(list(accountNms)))

    result: dict[str, float] = {}
    for row in matched.iter_rows(named=True):
        code = row.get(scCol, "")
        if code and code not in result:
            val = parseNumStr(row.get(amountCol))
            if val is not None:
                result[code] = val

    return result


_VALUATION_REQUIRED_COLS: tuple[str, ...] = (
    "stockCode",
    "marketCap",
    "per",
    "pbr",
    "dividendYield",
    "current",
    "snapshotAt",
)


def loadValuationSnapshot() -> tuple[pl.DataFrame | None, datetime | None]:
    """일일 prebuild 된 밸류에이션 스냅샷 parquet 로드.

    ``dart/scan/valuation.parquet`` 는 GH Actions cron (KST 04:00) 이 네이버 API 에서
    시가총액·PER·PBR·배당수익률·현재가를 전종목 수집해 HuggingFace 에 배포한 파일이다.
    ``_ensureScanData()`` 가 HF 자동 다운로드를 보장한다.

    Returns
    -------
    frame : pl.DataFrame | None
        prebuild snapshot. 필수 컬럼 누락이나 파일 부재 시 ``None``.
    snapshotAt : datetime | None
        수집 시각 (UTC). 파일 부재 시 ``None``.

    Notes
    -----
    - 호출자는 ``None`` 인 경우 네이버 실시간 수집 (``_fetchAll``) 으로 fallback 한다.
    - 스냅샷이 1일 이상 오래된 경우 상위 경로 ``_maybeWarnStale("scan")`` 가 경고.
    """
    scanDir = _ensureScanData()
    path = scanDir / "valuation.parquet"
    if not path.exists():
        return None, None
    try:
        frame = pl.read_parquet(str(path))
    except (pl.exceptions.PolarsError, OSError):
        return None, None
    missing = [c for c in _VALUATION_REQUIRED_COLS if c not in frame.columns]
    if missing:
        return None, None
    if frame.is_empty():
        return None, None
    first = frame["snapshotAt"][0]
    if isinstance(first, datetime):
        snapshotAt: datetime | None = first
    else:
        try:
            snapshotAt = datetime.fromisoformat(str(first))
        except (TypeError, ValueError):
            snapshotAt = None
    return frame, snapshotAt


def scanFinanceParquets(
    statement: str,
    accountIds: set[str],
    accountNms: set[str],
    *,
    amountCol: str = "thstrm_amount",
) -> dict[str, float]:
    """finance parquet 전수 스캔 → 종목별 계정 값.

    scan/finance.parquet 프리빌드가 있으면 단일 파일에서 즉시 필터.
    없으면 종목별 parquet 순회 (fallback).

    Parameters
    ----------
    statement : str
        재무제표 구분 (예: "IS", "BS", "CF").
    account_ids : set[str]
        매칭할 account_id 집합.
    account_nms : set[str]
        매칭할 account_nm 집합.
    amount_col : str
        금액 컬럼명 (기본 "thstrm_amount").

    Returns
    -------
    dict[str, float]
        {종목코드: 금액(원)} — 종목별 최신 연도 첫 매칭 계정의 값.
    """
    sj_divs = [statement] if statement != "IS" else ["IS", "CIS"]

    # 1순위: 프리빌드 scan parquet (없으면 자동 다운로드 시도)
    scanDir = _ensureScanData()
    scan_path = scanDir / "finance.parquet"
    if scan_path.exists():
        try:
            return _scanFinanceFromMerged(scan_path, sj_divs, accountIds, accountNms, amountCol)
        except (pl.exceptions.PolarsError, OSError):
            pass  # fallback

    # 2순위: 종목별 순회 (fallback)
    from dartlab.core.dataLoader import _dataDir

    finance_dir = Path(_dataDir("finance"))
    parquet_files = sorted(finance_dir.glob("*.parquet"))

    result: dict[str, float] = {}
    for pf in parquet_files:
        code = pf.stem
        try:
            # lazy scan: 필터를 Rust 엔진으로 밀어넣어 메모리 절감
            target = (
                pl.scan_parquet(str(pf))
                .filter(
                    pl.col("sj_div").is_in(sj_divs)
                    & (pl.col("fs_nm").str.contains("연결") | pl.col("fs_nm").str.contains("재무제표"))
                )
                .collect()
            )
        except (pl.exceptions.PolarsError, OSError):
            continue

        if target.is_empty() or "account_id" not in target.columns:
            continue

        cfs = target.filter(pl.col("fs_nm").str.contains("연결"))
        target = cfs if not cfs.is_empty() else target

        years = sorted(target["bsns_year"].unique().to_list(), reverse=True)
        if not years:
            continue
        latest = target.filter(pl.col("bsns_year") == years[0])

        for row in latest.iter_rows(named=True):
            aid = row.get("account_id", "")
            anm = row.get("account_nm", "")
            val = parseNumStr(row.get(amountCol))
            if (aid in accountIds or anm in accountNms) and val is not None:
                result[code] = val
                break

    return result
