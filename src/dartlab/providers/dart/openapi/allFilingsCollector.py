"""전체 공시 원문 수집기 — 2단계 증분 수집 + raw HTML 전체 태그 보존.

Phase 1: 목록 수집 (collectMeta) — 일자별 API 1회, 매우 가볍다.
Phase 2: 원문 수집 (fillContent) — 건당 API 1회, 키 소비 큼. 본문은 zip 안 largest
HTML 파일을 *raw 그대로* (`content_html` 컬럼) 저장한다. 태그·테이블·구조 모두
보존. plain text 가 필요한 소비자는 BeautifulSoup `get_text()` 등으로 변환.

목록을 먼저 전부 모은 뒤, 원문은 키 여유 있을 때 점진적으로 채운다.

사용법::

    from dartlab.providers.dart.openapi.allFilingsCollector import (
        collectMetaRange, fillContent, stats
    )

    # Phase 1: 목록만 빠르게 (5년치도 키 1개로 가능)
    collectMetaRange("20210401", "20260330")

    # Phase 2: 원문 채우기 (일자별, 키 여유 있을 때)
    fillContent("20260327")
    fillContentAll()  # 미수집 원문 전체
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import polars as pl

import dartlab.config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger
from dartlab.core.memory import withMemoryBudget
from dartlab.providers.dart.openapi.client import DartClient
from dartlab.providers.dart.openapi.disclosure import listFilings

_log = getLogger(__name__)

# ── 상수 ──

_ALLFILINGS_DIR_KEY = "allFilings"
_META_SUFFIX = "_meta"  # 목록만: 20260327_meta.parquet
# 원문포함: 20260327.parquet

# 정기공시 (사업/분기/반기보고서) 는 `data/dart/docs/` 가 owner — allFilings 본문 수집에서 스킵.
# 89% 가 docs/ 와 중복 (2026-05 검증). 부피 큰 공시 본문 중복 호출 차단.
_PERIODIC_REPORT_PATTERNS: tuple[str, ...] = ("사업보고서", "분기보고서", "반기보고서")

# ── 내부 유틸 ──


def _allFilingsDir() -> Path:
    """allFilings parquet 저장 디렉토리."""
    root = Path(_cfg.dataDir)
    d = root / DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _collectOneHtml(client: DartClient, rceptNo: str) -> str | None:
    """단일 공시 원문 raw HTML 반환 — 모든 태그·테이블·구조 보존.

    zip 안 largest 파일을 utf-8/euc-kr/cp949 순으로 디코딩만 한다. 후처리 0.
    빈 문자열·디코딩 실패는 None.
    """
    try:
        raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
    except (RuntimeError, OSError):
        return None

    if raw is None:
        return None

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        return None

    names = zf.namelist()
    if not names:
        return None

    largest = max(names, key=lambda n: zf.getinfo(n).file_size)
    content = zf.read(largest)

    htmlContent: str | None = None
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            htmlContent = content.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if htmlContent is None:
        htmlContent = content.decode("utf-8", errors="replace")

    if not htmlContent.strip():
        return None

    return htmlContent


# ═══════════════════════════════════════════
# Phase 1: 목록 수집 (가볍다 — 일자당 API ~15회)
# ═══════════════════════════════════════════


def collectMetaDay(
    period: str,
    *,
    client: DartClient | None = None,
    corpClasses: list[str] | None = None,
    showProgress: bool = True,
) -> pl.DataFrame | None:
    """하루치 공시 목록만 수집 → _meta.parquet 저장.

    이미 목록이 있거나 원문까지 완료된 날짜는 건너뛴다.

    Args:
        period: 인자.
        client: 인자.
        corpClasses: 인자.
        showProgress: 인자.

    Raises:
        없음.

    Example:
        >>> collectMetaDay(...)

    Returns:
        pl.DataFrame 또는 None — 수집 결과.
    """
    if client is None:
        client = DartClient()

    if corpClasses is None:
        corpClasses = ["Y", "K"]

    outDir = _allFilingsDir()
    metaPath = outDir / f"{period}{_META_SUFFIX}.parquet"
    fullPath = outDir / f"{period}.parquet"

    # 원문까지 완료됐거나 목록이 있으면 건너뜀
    if fullPath.exists():
        if showProgress:
            _log.info("[%s] 원문 수집 완료됨", period)
        return None
    if metaPath.exists():
        if showProgress:
            df = pl.read_parquet(metaPath)
            _log.info("[%s] 목록 있음 (%d건)", period, df.height)
        return None

    meta = listFilings(client, start=period, end=period, fetchAll=True)
    if meta.height == 0:
        if showProgress:
            _log.info("[%s] 공시 없음 (휴일)", period)
        return None

    if corpClasses:
        meta = meta.filter(pl.col("corp_cls").is_in(corpClasses))

    if meta.height == 0:
        if showProgress:
            _log.info("[%s] 상장사 공시 없음", period)
        return None

    # 저장
    tmpPath = metaPath.with_suffix(".parquet.tmp")
    meta.write_parquet(tmpPath)
    tmpPath.rename(metaPath)

    if showProgress:
        _log.info("[%s] 목록 %d건 저장", period, meta.height)

    return meta


def collectMetaRange(
    startDate: str,
    endDate: str,
    *,
    client: DartClient | None = None,
    corpClasses: list[str] | None = None,
    showProgress: bool = True,
) -> int:
    """날짜 범위 목록 일괄 수집. 최신→과거 순. 매우 가볍다.

    Returns
    -------
    int
        수집된 날짜 수.

    Raises:
        없음.

    Example:
        >>> collectMetaRange(...)

    Args:
        startDate: 시작일 (YYYYMMDD).
        endDate: 종료일 (YYYYMMDD).
        client: DartClient 인스턴스. None 이면 자동 생성.
        corpClasses: 회사 종류 필터 (KOSPI/KOSDAQ/etc). None 이면 전체.
        showProgress: True 면 progress 로그 출력.

    Returns:
        int — 수집 건수.
    """
    from datetime import datetime, timedelta

    if client is None:
        client = DartClient()

    start = datetime.strptime(startDate, "%Y%m%d")
    end = datetime.strptime(endDate, "%Y%m%d")

    dates = []
    current = end
    while current >= start:
        dates.append(current.strftime("%Y%m%d"))
        current -= timedelta(days=1)

    collected = 0
    for i, date in enumerate(dates):
        if showProgress and (i + 1) % 10 == 0:
            _log.info("--- 목록 진행: %d/%d ---", i + 1, len(dates))
        result = collectMetaDay(
            date,
            client=client,
            corpClasses=corpClasses,
            showProgress=showProgress,
        )
        if result is not None:
            collected += 1

    if showProgress:
        _log.info("목록 수집 완료: %d일", collected)

    return collected


# ═══════════════════════════════════════════
# Phase 2: 원문 채우기 (무겁다 — 건당 API 1회)
# ═══════════════════════════════════════════


def fillContent(
    period: str,
    *,
    client: DartClient | None = None,
    showProgress: bool = True,
) -> pl.DataFrame | None:
    """하루치 목록의 원문을 채운다. _meta.parquet → .parquet 승격.

    이미 원문이 있는 날짜는 건너뛴다.

    Args:
        period: 인자.
        client: 인자.
        showProgress: 인자.

    Raises:
        없음.

    Example:
        >>> fillContent(...)

    Returns:
        pl.DataFrame 또는 None — 수집 결과.
    """
    if client is None:
        client = DartClient()

    outDir = _allFilingsDir()
    metaPath = outDir / f"{period}{_META_SUFFIX}.parquet"
    fullPath = outDir / f"{period}.parquet"

    # 원문 완료 → 건너뜀
    if fullPath.exists():
        if showProgress:
            _log.info("[%s] 원문 이미 완료", period)
        return None

    # 목록 없음
    if not metaPath.exists():
        if showProgress:
            _log.info("[%s] 목록 없음 (먼저 collectMetaDay 실행)", period)
        return None

    meta = pl.read_parquet(metaPath)
    total = meta.height

    if showProgress:
        _log.info("[%s] %d건 원문 수집 시작", period, total)

    allRows: list[dict] = []
    success = empty = skippedPeriodic = 0

    for idx, row in enumerate(meta.iter_rows(named=True)):
        rceptNo = row["rcept_no"]
        reportNm = row.get("report_nm", "") or ""

        # 정기공시 스킵 — docs/ 가 owner.
        if any(p in reportNm for p in _PERIODIC_REPORT_PATTERNS):
            skippedPeriodic += 1
            continue

        html = _collectOneHtml(client, rceptNo)

        if html:
            success += 1
        else:
            empty += 1

        allRows.append(
            {
                "corp_code": row["corp_code"],
                "corp_name": row["corp_name"],
                "stock_code": row.get("stock_code", ""),
                "corp_cls": row["corp_cls"],
                "rcept_dt": row["rcept_dt"],
                "rcept_no": rceptNo,
                "report_nm": row["report_nm"],
                "flr_nm": row.get("flr_nm", ""),
                "content_html": html,
            }
        )

        if showProgress and (idx + 1) % 100 == 0:
            _log.info("  [%d/%d] 성공=%d 빈=%d", idx + 1, total, success, empty)

    if not allRows:
        return None

    # 안전장치 — 본문 0 건 성공이면 .parquet 으로 승격 X, _meta 유지.
    # 과거 사고 (2025-04 ~ 2026-02, 222 일치) 재발 방지: API 키 한도 / 네트워크 실패로
    # 전 row 가 empty 로 끝나도 빈 .parquet 으로 저장되어 영구 데드락 마킹됐었다.
    # 본 가드는 *0 건 성공 = 수집 실패* 로 간주하고 retry 가능 상태로 유지한다.
    # (정기공시만 있는 날은 skippedPeriodic > 0 이지만 success > 0 보장 안 됨 — 정기공시만 있는 날은
    #  처리 대상 0 건이라 빈 본문 .parquet 가 합법이라 별도 분기 불필요.)
    if success == 0 and (success + empty) > 0:
        _log.warning(
            "[%s] 본문 수집 0 건 (시도 %d 건 모두 empty, 정기공시 %d 건 skip) — .parquet 승격 차단, _meta 보존. "
            "원인 확인 후 재시도 필요 (API 키 한도 / 네트워크 / URL 변경 가능).",
            period,
            empty,
            skippedPeriodic,
        )
        return None

    df = pl.DataFrame(allRows)

    # 원자적 저장 → .parquet (원문 완료)
    tmpPath = fullPath.with_suffix(".parquet.tmp")
    df.write_parquet(tmpPath)
    tmpPath.rename(fullPath)

    # _meta 제거 (승격 완료)
    if metaPath.exists():
        metaPath.unlink()

    if showProgress:
        _log.info(
            "[%s] 완료: %d건 성공, %d건 빈, %d건 정기공시 skip(→docs/), %d행, %.1fMB",
            period,
            success,
            empty,
            skippedPeriodic,
            df.height,
            fullPath.stat().st_size / 1024 / 1024,
        )

    return df


def fillContentAll(
    *,
    client: DartClient | None = None,
    showProgress: bool = True,
) -> int:
    """목록만 있는 날짜 전체의 원문을 채운다. 최신순.

    Returns
    -------
    int
        원문 수집 완료한 날짜 수.

    Raises:
        없음.

    Example:
        >>> fillContentAll(...)

    Args:
        client: DartClient 인스턴스. None 이면 자동 생성.
        showProgress: True 면 progress 로그 출력.

    Returns:
        int — 수집 건수.
    """
    if client is None:
        client = DartClient()

    pending = pendingDates()
    if not pending:
        if showProgress:
            _log.info("원문 미수집 날짜 없음")
        return 0

    if showProgress:
        _log.info("원문 미수집 %d일 처리 시작", len(pending))

    filled = 0
    for i, date in enumerate(pending):
        if showProgress:
            _log.info("=== [%d/%d] ===", i + 1, len(pending))
        try:
            result = fillContent(date, client=client, showProgress=showProgress)
            if result is not None:
                filled += 1
        except Exception as e:  # noqa: BLE001
            if showProgress:
                _log.warning("[%s] 에러: %s", date, e)
            break  # API 한도 초과 등이면 중단

    if showProgress:
        _log.info("원문 수집 완료: %d일", filled)

    return filled


# ═══════════════════════════════════════════
# 조회/통계
# ═══════════════════════════════════════════


def collectedDates() -> list[str]:
    """원문 수집 완료된 날짜 목록 (최신순).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> collectedDates(...)

    Returns:
        list[str] — 결과 목록.
    """
    outDir = _allFilingsDir()
    dates = sorted(
        [p.stem for p in outDir.glob("*.parquet") if len(p.stem) == 8 and p.stem.isdigit()],
        reverse=True,
    )
    return dates


def pendingDates() -> list[str]:
    """목록만 있고 원문 미수집인 날짜 목록 (최신순).

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> pendingDates(...)

    Returns:
        list[str] — 결과 목록.
    """
    outDir = _allFilingsDir()
    dates = sorted(
        [p.stem.replace(_META_SUFFIX, "") for p in outDir.glob(f"*{_META_SUFFIX}.parquet")],
        reverse=True,
    )
    return dates


def loadDay(period: str) -> pl.DataFrame | None:
    """수집된 하루치 데이터 로드.

    Args:
        period: 인자.

    Raises:
        없음.

    Example:
        >>> loadDay(...)

    Returns:
        pl.DataFrame 또는 None — 수집 결과.
    """
    path = _allFilingsDir() / f"{period}.parquet"
    if not path.exists():
        return None
    return pl.read_parquet(path)


@withMemoryBudget(limitMb=500)
def loadAll() -> pl.DataFrame:
    """원문 수집 완료된 전체 데이터 로드.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> loadAll(...)

    Returns:
        pl.DataFrame — 결과.
    """
    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
    if not files:
        return pl.DataFrame()
    return pl.scan_parquet(files).collect(engine="streaming")


def stats() -> dict:
    """수집 현황 통계.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> stats(...)

    Returns:
        dict — 결과 dict.
    """
    completed = collectedDates()
    pending = pendingDates()

    outDir = _allFilingsDir()
    totalSize = 0
    totalRows = 0
    totalFilings = 0

    for d in completed:
        path = outDir / f"{d}.parquet"
        totalSize += path.stat().st_size
        df = pl.scan_parquet(path).select("rcept_no").collect(engine="streaming")
        totalRows += df.height
        totalFilings += df["rcept_no"].n_unique()

    pendingFilings = 0
    for d in pending:
        path = outDir / f"{d}{_META_SUFFIX}.parquet"
        df = pl.scan_parquet(path).select("rcept_no").collect(engine="streaming")
        pendingFilings += df["rcept_no"].n_unique()

    return {
        "completedDays": len(completed),
        "pendingDays": len(pending),
        "filings": totalFilings,
        "pendingFilings": pendingFilings,
        "rows": totalRows,
        "sizeMb": round(totalSize / 1024 / 1024, 1),
        "firstDate": completed[-1] if completed else None,
        "lastDate": completed[0] if completed else None,
    }
