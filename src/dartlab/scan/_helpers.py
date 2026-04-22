"""scan 공용 유틸리티 — report parquet 스캔, 숫자 파싱, listing 로드."""

from __future__ import annotations

import time
from pathlib import Path

import polars as pl

_scanDownloaded = False

# scan 프리빌드 freshness — HF 수집 주기(일 1회)에 맞춰 24h TTL
_SCAN_FRESHNESS_TTL_SECONDS = 24 * 3600

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

    루트 필수 파일(finance/changes/sharesOutstanding)이 모두 존재하고 TTL(24h)
    이내면 즉시 반환 (HF 호출 0). 하나라도 없거나 TTL 초과면 다운로드 시도.

    Returns
    -------
    Path
        scan 프리빌드 디렉토리 경로 (~/.dartlab/data/scan/).
    """
    from dartlab.core.dataLoader import _dataDir
    from dartlab.core.messaging import emit

    scanDir = Path(_dataDir("scan"))

    global _scanDownloaded
    if _scanDownloaded:
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


def scan_parquets(api_type: str, keep_cols: list[str]) -> pl.DataFrame:
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
    scan_path = scanDir / "report" / f"{api_type}.parquet"
    if scan_path.exists():
        try:
            lf = pl.scan_parquet(str(scan_path))
            schema_names = lf.collect_schema().names()
            available = [c for c in keep_cols if c in schema_names]
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
        from dartlab.core.guidance import emit

        emit("hint:market_data_needed", category="report", fn=api_type)
        return pl.DataFrame()

    frames: list[pl.LazyFrame] = []
    for pf in parquet_files:
        try:
            lf = pl.scan_parquet(str(pf))
            schema_names = lf.collect_schema().names()
            if "apiType" not in schema_names:
                continue
            available = [c for c in keep_cols if c in schema_names]
            non_meta = [c for c in available if c not in ("stockCode", "year", "quarter")]
            if not non_meta:
                continue
            lf = lf.filter(pl.col("apiType") == api_type).select(available)
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


def parse_num(s) -> float | None:
    """문자열/숫자 → float 변환.

    Parameters
    ----------
    s : str | int | float | None
        변환 대상. 쉼표/공백 포함 문자열도 처리.

    Returns
    -------
    float | None
        숫자 변환 결과. 변환 불가면 None.

    Notes
    -----
    core.finance.helpers.parseNumStr 이 SSOT.
    """
    if isinstance(s, (int, float)):
        return float(s)
    from dartlab.core.finance.helpers import parseNumStr

    return parseNumStr(s)


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
            val = parse_num(row.get(amtCol))
            if val is not None:
                return val
    return None


def find_latest_year(raw: pl.DataFrame, check_col: str, min_count: int = 500) -> str | None:
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
        ok = sub.filter(pl.col(check_col).is_not_null() & (pl.col(check_col) != "-") & (pl.col(check_col) != "")).shape[
            0
        ]
        if ok >= min_count:
            return y
    return None


QUARTER_ORDER = {"2분기": 1, "4분기": 2, "3분기": 3, "1분기": 4}


def pick_best_quarter(df: pl.DataFrame) -> pl.DataFrame:
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


def load_listing():
    """상장사 목록 로드.

    Returns
    -------
    pl.DataFrame
        종목코드, 종목명, 업종 등 상장사 기본 정보.

    Notes
    -----
    network/scanner.py 의 load_listing 에 위임.
    """
    from dartlab.scan.network.scanner import load_listing as _ll

    return _ll()


def parse_date_year(s) -> int | None:
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
            val = parse_num(row.get(amountCol))
            if val is not None:
                result[code] = val

    return result


def scan_finance_parquets(
    statement: str,
    account_ids: set[str],
    account_nms: set[str],
    *,
    amount_col: str = "thstrm_amount",
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
            return _scanFinanceFromMerged(scan_path, sj_divs, account_ids, account_nms, amount_col)
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
            val = parse_num(row.get(amount_col))
            if (aid in account_ids or anm in account_nms) and val is not None:
                result[code] = val
                break

    return result
