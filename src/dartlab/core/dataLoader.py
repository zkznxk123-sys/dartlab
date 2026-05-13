"""데이터 로딩 및 공통 유틸."""

import json
import sys
import time
from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path

import polars as pl

from dartlab.core.dataConfig import (
    DATA_RELEASES,
    HF_REPO,
    hfBaseUrl,
)
from dartlab.core.dataLoaderNormalize import CATEGORICAL_COLS as _CATEGORICAL_COLS
from dartlab.core.dataLoaderNormalize import DOWNCAST_INT_COLS as _DOWNCAST_INT_COLS

_IS_PYODIDE = sys.platform == "emscripten"

# ── loadData LRU (parquet 재로드 방지) ──
# 같은 (stockCode, category, …) 조합이 여러 calc 에서 반복 호출될 때 disk
# 재파싱을 막는다. accessor 레벨 캐시(Company._cache 의 _financeStmt_*)가
# BoundedCache 에 의해 evict 되어도 이 캐시가 남아있으면 loadData 는 disk
# 를 다시 건들이지 않는다. 결과는 이미 메모리 상 DataFrame 이므로 복제
# 오버헤드 없음.
#
# max_entries 는 작게 유지: (stockCode × category=4) × 사용자 분석 빈도 =
# 일반 세션 8~16. 초과분은 LRU evict.
_LOAD_CACHE: "OrderedDict[tuple, pl.DataFrame]" = OrderedDict()
# 회사 1 개 docs DataFrame 이 ~수백 MB (대기업 + 10 년치) 라 16 entry 보유 시
# 수 GB 잠재 점유. CLAUDE.md 병렬 에이전트 2 × 카테고리 4 = 8 이 정합. LRU 압박이
# 잦으면 BoundedCache pinned (_finance_ 등) 가 in-memory 재사용을 잡는다.
_LOAD_CACHE_MAX = 8


def _clearLoadCache() -> None:
    """BoundedCache EMERGENCY 시 호출 — disk 캐시까지 비운다."""
    _LOAD_CACHE.clear()


def readParquetSafe(path) -> pl.DataFrame:
    """polars read_parquet with pyarrow fallback (pyodide WASM 호환).

    polars WASM wheel은 read_parquet이 비활성이므로
    pyarrow.parquet.read_table → pl.from_arrow 로 우회한다.
    일반 환경에서는 pl.read_parquet 그대로 사용.
    """
    if not _IS_PYODIDE:
        return pl.read_parquet(path)
    import io

    import pyarrow.parquet as pq

    data = Path(path).read_bytes() if not isinstance(path, bytes) else path
    arrow_table = pq.read_table(io.BytesIO(data))
    try:
        return pl.from_arrow(arrow_table)
    except (ModuleNotFoundError, ImportError):
        return pl.DataFrame(arrow_table.to_pydict())


if not _IS_PYODIDE:
    import socket
    from urllib.error import URLError
    from urllib.request import Request, urlopen, urlretrieve


def _getDataRoot() -> Path:
    from dartlab import config

    return Path(config.dataDir)


_DOWNLOAD_TIMEOUT = 30
_MAX_RETRIES = 3
_EDGAR_UNIVERSE_TTL_HOURS = 24
_DART_FRESHNESS_TTL_HOURS = 12  # 일일 HF 수집 주기(03:00 KST)에 맞춰 12h — 최대 stale 윈도우 반감
_KRX_FRESHNESS_TTL_HOURS = 1  # 장마감 후 일별 갱신 데이터라 stale 허용폭을 짧게 둔다
_SEC_HEADERS = {"User-Agent": "DartLab eddmpython@gmail.com"}
_LISTED_EXCHANGES = {"Nasdaq", "NYSE", "CBOE"}

PERIOD_KINDS = {
    "y": ["annual"],
    "q": ["Q1", "semi", "Q3", "annual"],
    "h": ["semi", "annual"],
}

_EXPLICIT_DOWNLOAD_ONLY_CATEGORIES = {"edgarDocs"}


@contextmanager
def _socketTimeout(seconds: int = _DOWNLOAD_TIMEOUT):
    """소켓 글로벌 타임아웃을 임시 설정하고 복원."""
    oldTimeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(seconds)
        yield
    finally:
        socket.setdefaulttimeout(oldTimeout)


def _dataDir(category: str = "docs") -> Path:
    return _getDataRoot() / DATA_RELEASES[category]["dir"]


def _downloadWithRetry(url: str, dest: Path) -> None:
    """URL → dest 다운로드. 최대 3회 재시도 (2초, 4초 대기)."""
    from dartlab.core.dataLoaderFreshness import downloadWithRetry

    downloadWithRetry(url, dest, maxRetries=_MAX_RETRIES, socketTimeout=_socketTimeout, urlretrieve=urlretrieve)


def _checkRemoteFreshness(stockCode: str, localPath: Path, category: str = "docs") -> bool | None:
    """로컬 파일이 원격보다 오래됐는지 HTTP HEAD로 확인.

    검증 2단계:
    1. ETag 비교 (HF의 content hash) — 다르면 stale
    2. Content-Length 비교 (HF가 알려준 파일 크기) — 다르면 stale
       → ETag만 같고 실제 내용/크기가 다른 손상 케이스 방어

    Returns: True=stale, False=fresh, None=판단불가(네트워크 오류 등).

    핵심 안전 규칙:
    - .etag 사이드카 파일은 **다운로드 성공 직후에만 작성**해야 한다 (_saveEtag).
    - 여기서 etag 파일이 없는 상태는 "이전에 다운로드 받은 적이 없거나, 외부 경로로
      복사된 stale 파일"이다. 어느 쪽이든 fresh로 판정하면 안 된다.
    - 과거 버그: etag 없으면 현재 HF ETag를 저장 + return False(fresh) → parquet은
      옛날 그대로인데 .etag만 새로 만들어져서 영구적으로 stale 데이터가 고정됨.
    - 수정: etag 없으면 stale(True) 반환하여 다운로드를 강제. _saveEtag가 다운로드
      성공 직후 etag를 기록한다.
    """
    from dartlab.core.dataLoaderFreshness import checkRemoteFreshness

    return checkRemoteFreshness(
        stockCode,
        localPath,
        category,
        hfBaseUrl=hfBaseUrl,
        fetchRemoteEtagAndSize=_fetchRemoteEtagAndSize,
    )


def _saveEtag(stockCode: str, dest: Path, category: str = "docs") -> None:
    """다운로드 성공 후 HF ETag를 사이드카 파일에 저장."""
    from dartlab.core.dataLoaderFreshness import saveEtag

    saveEtag(stockCode, dest, category, hfBaseUrl=hfBaseUrl, fetchRemoteEtag=_fetchRemoteEtag)


def _fetchRemoteEtag(url: str) -> str:
    """HTTP HEAD로 원격 ETag 조회. 없으면 빈 문자열."""
    etag, _ = _fetchRemoteEtagAndSize(url)
    return etag


def _fetchRemoteEtagAndSize(url: str) -> tuple[str, int]:
    """HTTP HEAD로 원격 ETag + Content-Length 동시 조회.

    HF는 LFS 파일에 대해 X-Linked-Size 헤더로 실제 파일 크기를 제공.
    일반 파일은 Content-Length. 둘 중 하나라도 있으면 사용.
    """
    req = Request(url, method="HEAD")
    with _socketTimeout(10):
        resp = urlopen(req)
    etag = resp.headers.get("ETag", "").strip('" ')
    sizeStr = resp.headers.get("X-Linked-Size") or resp.headers.get("Content-Length") or "0"
    try:
        size = int(sizeStr)
    except (ValueError, TypeError):
        size = 0
    return etag, size


def _download(stockCode: str, dest: Path, category: str = "docs") -> None:
    """HuggingFace 데이터셋에서 단건 다운로드."""
    hfUrl = f"{hfBaseUrl(category)}/{stockCode}.parquet"
    _downloadWithRetry(hfUrl, dest)
    _saveEtag(stockCode, dest, category)


_STALE_WARN_DAYS = 7  # 로컬 데이터가 7일 이상 갱신 안 됐을 때 사용자에게 경고
_staleWarnedPaths: set[str] = set()  # 세션당 경로별 1회만 경고


def _maybeWarnStale(path: Path) -> None:
    """로컬 데이터가 매우 오래됐으면(7일+) 한 번 경고. 같은 세션에서 같은 경로는 중복 안 함."""
    from dartlab.core.dataLoaderFreshness import maybeWarnStale

    maybeWarnStale(path, warnedPaths=_staleWarnedPaths, staleWarnDays=_STALE_WARN_DAYS)


def _shouldRefreshDart(path: Path, refresh: str) -> bool:
    """DART 카테고리 로컬 파일의 갱신 필요 여부 판단."""
    from dartlab.core.dataLoaderFreshness import shouldRefreshDart

    return shouldRefreshDart(
        path,
        refresh,
        staleWarnDays=_STALE_WARN_DAYS,
        dartFreshnessTtlHours=_DART_FRESHNESS_TTL_HOURS,
        warnStale=_maybeWarnStale,
    )


def _shouldRefreshHfCategory(path: Path, category: str, refresh: str) -> bool:
    """HF 공개 parquet 카테고리별 freshness 정책."""
    from dartlab.core.dataLoaderFreshness import shouldRefreshHfCategory

    return shouldRefreshHfCategory(
        path,
        category,
        refresh,
        krxFreshnessTtlHours=_KRX_FRESHNESS_TTL_HOURS,
        shouldRefreshDartFunc=_shouldRefreshDart,
    )


def _refreshFromHf(stockCode: str, path: Path, category: str) -> None:
    """ETag 비교 후 HF가 최신이면 다운로드로 갱신. 실패 시 기존 파일 유지."""
    from dartlab.core.dataLoaderFreshness import refreshFromHf

    refreshFromHf(
        stockCode,
        path,
        category,
        dataReleases=DATA_RELEASES,
        hfBaseUrl=hfBaseUrl,
        checkRemoteFreshness=_checkRemoteFreshness,
        downloadWithRetry=_downloadWithRetry,
        saveEtag=_saveEtag,
    )


def repairLocalCache(category: str = "finance", *, dryRun: bool = False) -> dict[str, int]:
    """로컬 dart 캐시 전수 무결성 검사 + 손상된 파일 자동 재다운로드.

    과거 ETag 사이드카 first-write 버그(_checkRemoteFreshness가 etag 없을 때
    현재 HF ETag를 그냥 저장하고 fresh 판정)로 인해 영구 stale로 굳어진 로컬
    parquet들을 전부 회복하기 위한 일괄 도구.

    검사 절차:
    1. 카테고리 폴더의 모든 *.parquet 순회
    2. 각각 _checkRemoteFreshness로 stale 판단 (ETag + Content-Length 2단계)
    3. stale이면 새 코드로 다운로드 (dryRun=True면 통계만)

    Args:
        category: "finance", "report", "docs" 중 하나
        dryRun: True면 다운로드 안 하고 통계만 반환

    Returns:
        {"checked": N, "stale": N, "repaired": N, "failed": N, "fresh": N}
    """
    dataDir = _dataDir(category)
    if not dataDir.exists():
        return {"checked": 0, "stale": 0, "repaired": 0, "failed": 0, "fresh": 0}

    stats = {"checked": 0, "stale": 0, "repaired": 0, "failed": 0, "fresh": 0}
    for parquet in sorted(dataDir.glob("*.parquet")):
        stockCode = parquet.stem
        stats["checked"] += 1
        stale = _checkRemoteFreshness(stockCode, parquet, category)
        if stale is None:
            stats["failed"] += 1
            continue
        if not stale:
            stats["fresh"] += 1
            continue
        stats["stale"] += 1
        if dryRun:
            continue
        try:
            _refreshFromHf(stockCode, parquet, category)
            stats["repaired"] += 1
        except (URLError, socket.timeout, OSError):
            stats["failed"] += 1
    return stats


def loadData(
    stockCode: str,
    category: str = "docs",
    *,
    sinceYear: int | None = None,
    asOf: str | None = None,
    refresh: str = "auto",
    columns: list[str] | None = None,
) -> pl.DataFrame:
    """종목코드 → DataFrame. 로컬에 없으면 릴리즈에서 자동 다운로드.

    `(stockCode, category, …)` 조합 결과는 프로세스 수명 동안 `_LOAD_CACHE`
    에 LRU(max 16) 캐시된다. accessor 레벨 캐시가 evict 되어도 disk 재파싱
    을 면해주어 대기업 + 다축 analysis 호출 시 메모리·시간 누적을 막는다.
    `refresh="force"` 는 캐시를 우회한다.
    """
    if _IS_PYODIDE:
        return _loadDataPyodide(stockCode, category, sinceYear=sinceYear, columns=columns)
    from dartlab.core.memory import checkMemoryAndGc

    dataDir = _dataDir(category)
    path = dataDir / f"{stockCode}.parquet"

    # KRX daily bulk data is updated after market close. In long-lived server
    # processes, the in-memory LRU must not pin yesterday's parquet after the
    # short KRX freshness TTL expires.
    krxShouldRefresh: bool | None = None
    if category in {"krxPrices", "krxIndices"} and refresh == "auto":
        krxShouldRefresh = _shouldRefreshHfCategory(path, category, refresh)

    # LRU cache 조회
    cacheKey = (stockCode, category, sinceYear, tuple(columns or ()), asOf, refresh)
    if refresh != "force" and krxShouldRefresh is not True:
        cached = _LOAD_CACHE.get(cacheKey)
        if cached is not None:
            _LOAD_CACHE.move_to_end(cacheKey)
            return cached

    checkMemoryAndGc(f"loadData({stockCode},{category})")
    effectiveSinceYear = sinceYear
    if category == "edgarDocs" and effectiveSinceYear is None:
        effectiveSinceYear = 2009
    if category == "edgarDocs":
        # registry dispatch (정공법 B — DIP). providers/edgar 가 EdgarDocsLoader 등록.
        from dartlab.core.loaders import getLoader

        loader = getLoader("edgarDocs")
        if loader is None:
            raise RuntimeError("edgarDocs LoaderProvider 미등록 — providers.edgar 모듈 로드 실패")
        loader.ensure(
            stockCode,
            path,
            sinceYear=effectiveSinceYear or 2009,
            asOf=asOf,
            refresh=refresh,
        )
    else:
        shouldRefresh = (
            krxShouldRefresh if krxShouldRefresh is not None else _shouldRefreshHfCategory(path, category, refresh)
        )
        _ensureLocalParquet(stockCode, path, category, shouldRefresh=shouldRefresh)
    # lazy scan: sinceYear 필터 또는 컬럼 프로젝션이 있으면 scan_parquet 사용
    yearColCandidates = ("year", "bsns_year")
    useLazy = sinceYear is not None or columns is not None
    if useLazy:
        lf = pl.scan_parquet(str(path))
        schemaNames = lf.collect_schema().names()
        # sinceYear 필터 (year 또는 bsns_year 컬럼)
        if sinceYear is not None:
            for colName in yearColCandidates:
                if colName in schemaNames:
                    yearCol = pl.col(colName)
                    if str(lf.collect_schema()[colName]) == "String":
                        yearCol = yearCol.cast(pl.Int32, strict=False)
                    lf = lf.filter(yearCol >= sinceYear)
                    break
        # 컬럼 프로젝션
        if columns:
            available = [c for c in columns if c in schemaNames]
            if available:
                lf = lf.select(available)
        # M2: streaming engine 명시 — filter + select 만 있는 단순 chain 은 호환 + O(batch) 메모리
        df = lf.collect(engine="streaming")
    else:
        df = pl.read_parquet(str(path))
    result = _normalizeLoadedFrame(df, category)

    # LRU 저장 (refresh="force" 여도 결과는 캐시에 남김 — 다음 auto 호출 재사용)
    _LOAD_CACHE[cacheKey] = result
    while len(_LOAD_CACHE) > _LOAD_CACHE_MAX:
        _LOAD_CACHE.popitem(last=False)
    return result


def _ensureLocalParquet(stockCode: str, path: Path, category: str, *, shouldRefresh: bool) -> None:
    """카테고리별 로컬 parquet 보장 (최초 로드 + refresh 통합 라우터).

    - ``edgar`` → SEC 벌크 (companyfacts.zip) 자동 다운로드·변환, HF 미러링 없음
    - 그 외 → HF 다운로드 + ETag 기반 증분 갱신
    """
    if category == "edgar":
        # registry dispatch (정공법 B — DIP). providers/edgar 가 EdgarBulkLoader 등록.
        from dartlab.core.loaders import getLoader

        loader = getLoader("edgar")
        if loader is None:
            raise RuntimeError("edgar LoaderProvider 미등록 — providers.edgar 모듈 로드 실패")
        loader.ensure(stockCode, path, refresh=shouldRefresh)
        return

    if not path.exists():
        _downloadFromHf(stockCode, path, category)
        return

    if shouldRefresh:
        _refreshFromHf(stockCode, path, category)


def _downloadFromHf(stockCode: str, path: Path, category: str) -> None:
    """HF 최초 다운로드 + 안내 + 예외 처리 단일 블록."""
    from dartlab.core.messaging import emit
    from dartlab.core.messaging import format as gfmt

    label = DATA_RELEASES[category]["label"]
    emit("download:start", stockCode=stockCode, label=label)
    try:
        _download(stockCode, path, category)
    except (URLError, socket.timeout, OSError) as e:
        if path.exists():
            path.unlink()
        raise RuntimeError(gfmt("error:download_failed", stockCode=stockCode, label=label, error=str(e))) from e
    except ValueError:
        if path.exists():
            path.unlink()
        raise

    size = path.stat().st_size
    sizeStr = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
    emit("download:done_short", sizeStr=sizeStr)


_HF_MAX_RETRIES = 3


def downloadAll(category: str = "docs", *, forceUpdate: bool = False) -> None:
    """HuggingFace 데이터셋에서 카테고리 전체 parquet을 다운로드.

    huggingface_hub의 snapshot_download를 사용하여 resume/병렬 다운로드를 지원한다.
    중간에 끊겨도 이어받기가 가능하며, 이미 받은 파일은 자동 skip.

    Args:
        category: "docs", "finance", "report" 등.
        forceUpdate: True면 로컬 캐시 무시하고 원격 최신 파일로 갱신.

    Examples::

        import dartlab
        dartlab.downloadAll("finance")              # 재무 전체 (~600MB)
        dartlab.downloadAll("docs")                 # 공시 전체 (~8GB)
        dartlab.downloadAll("finance", forceUpdate=True)  # 강제 갱신
    """
    if category in _EXPLICIT_DOWNLOAD_ONLY_CATEGORIES:
        raise ValueError(
            f"{category}는 전체 다운로드를 지원하지 않음. 개별 종목 loadData(..., category='{category}')를 사용하세요."
        )

    # Pyodide (WASM 브라우저) 는 huggingface_hub 가 설치 안 되고 전체 다운로드가 용량상
    # 부적합. scan 카테고리만 경량 `finance-lite.parquet`(~18MB) 을 pyfetch 로 개별 수신.
    if _IS_PYODIDE:
        if category == "scan":
            _pyodideFetchScanLite()
            return
        raise NotImplementedError(
            f"Pyodide 환경에서 downloadAll('{category}') 는 지원하지 않습니다. "
            "scan 은 'finance-lite' 경량본만 지원되며 개별 종목은 Company() 로 자동 수신됩니다."
        )

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise ImportError(
            "downloadAll()은 huggingface_hub가 필요합니다.\n"
            "또는 개별 종목은 dartlab.Company('005930')으로 자동 다운로드됩니다."
        ) from exc

    import os

    dataDir = _dataDir(category)
    dataDir.mkdir(parents=True, exist_ok=True)
    label = DATA_RELEASES[category]["label"]
    hfDir = DATA_RELEASES[category]["dir"]

    from dartlab.core.messaging import emit

    emit("download_all:hf_start", label=label, repo=HF_REPO, dir=hfDir)

    # rate limit 방지: 동시 다운로드 workers를 보수적으로 설정
    if "HF_HUB_DOWNLOAD_WORKERS" not in os.environ:
        os.environ["HF_HUB_DOWNLOAD_WORKERS"] = "4"

    localDir = _getDataRoot()
    lastErr = None
    for attempt in range(_HF_MAX_RETRIES):
        try:
            # scan 은 루트(finance.parquet 등) + 하위 폴더(report/) 둘 다 받아야 한다.
            # huggingface_hub 의 allow_patterns 는 fnmatch — `**` 가 특수문자가 아니라
            # 중간 디렉토리 최소 1개를 강제한다. `dart/scan/**/*.parquet` 는 루트 파일을
            # 제외시키므로 두 패턴을 모두 넘겨야 finance.parquet 같은 루트 파일까지 받아진다.
            pattern = [f"{hfDir}/*.parquet", f"{hfDir}/**/*.parquet"] if category == "scan" else f"{hfDir}/*.parquet"
            snapshot_download(
                repo_id=HF_REPO,
                repo_type="dataset",
                local_dir=str(localDir),
                allow_patterns=pattern,
                force_download=forceUpdate if attempt == 0 else False,
            )
            break
        except (OSError, ConnectionError, TimeoutError) as exc:
            lastErr = exc
            emit("download_all:hf_retry", attempt=attempt + 1, error=str(exc))
            if attempt < _HF_MAX_RETRIES - 1:
                time.sleep(2 ** (attempt + 1))
    else:
        raise RuntimeError(
            f"{label} 다운로드 실패 ({_HF_MAX_RETRIES}회 재시도 후). "
            f"네트워크를 확인하거나 HF 토큰을 설정하세요: huggingface-cli login\n"
            f"마지막 에러: {lastErr}"
        )

    globPattern = "**/*.parquet" if category == "scan" else "*.parquet"
    fileCount = len(list(dataDir.glob(globPattern)))
    # scan은 테마별 parquet (안에 전종목 포함) → 파일 수 ≠ 종목 수
    countLabel = f"{fileCount}파일" if category == "scan" else f"{fileCount}종목"
    emit("download_all:hf_done", label=label, count=countLabel, dataDir=str(dataDir))

    # scan 은 finance.parquet 이 핵심 산출물. allow_patterns 회귀 등으로
    # 조용히 누락되면 상위 fallback 경로가 부분 결과(예: 종목 2개)를 전수인 양
    # 반환하는 심각한 오동작이 발생한다. 필수 파일 존재를 강제 검증.
    if category == "scan":
        required = ("finance.parquet",)
        missing = [name for name in required if not (dataDir / name).exists()]
        if missing:
            emit("scan:prebuild_incomplete", missing=missing)
            raise RuntimeError(
                f"scan 프리빌드 다운로드가 불완전합니다 (누락: {missing}). "
                f"네트워크 확인 후 dartlab.downloadAll('scan', forceUpdate=True) 로 재시도하세요."
            )


def download(stockCode: str) -> None:
    """특정 종목의 docs + finance + report 데이터를 모두 다운로드."""
    from dartlab.core.messaging import emit

    for category in DATA_RELEASES:
        if category in _EXPLICIT_DOWNLOAD_ONLY_CATEGORIES:
            continue
        dataDir = _dataDir(category)
        dest = dataDir / f"{stockCode}.parquet"
        label = DATA_RELEASES[category]["label"]
        if dest.exists():
            emit("download:exists", stockCode=stockCode, label=label)
            continue
        emit("download:progress", stockCode=stockCode, label=label)
        try:
            _download(stockCode, dest, category)
            size = dest.stat().st_size
            sizeStr = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
            emit("download:done", label=label, sizeStr=sizeStr)
        except (URLError, socket.timeout, OSError) as e:
            if dest.exists():
                dest.unlink()
            emit("download:failed_single", stockCode=stockCode, label=label, error=str(e))


DART_VIEWER = "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="

EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_LISTED_UNIVERSE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"


def buildIndex(category: str = "docs") -> pl.DataFrame:
    """로컬 parquet 전체를 스캔해서 종목 인덱스 생성.

    Returns:
        DataFrame (stockCode, corpName, rows, yearFrom, yearTo, nDocs)
        로컬에 파일이 없으면 빈 DataFrame.
    """
    dataDir = _dataDir(category)
    files = sorted(dataDir.glob("*.parquet"))
    if not files:
        return pl.DataFrame(
            schema={
                "stockCode": pl.Utf8,
                "corpName": pl.Utf8,
                "rows": pl.Int64,
                "yearFrom": pl.Utf8,
                "yearTo": pl.Utf8,
                "nDocs": pl.Int64,
            }
        )

    from rich.progress import Progress

    records = []
    with Progress() as progress:
        _task = progress.add_task("종목 스캔", total=len(files))
        for f in files:
            df = _normalizeLoadedFrame(pl.read_parquet(str(f)), category)
            code = f.stem
            name = extractCorpName(df)
            years = sorted(df["year"].unique().to_list())
            docIdCol = _docIdColumn(df)
            nDocs = df[docIdCol].n_unique() if docIdCol else 0
            records.append(
                {
                    "stockCode": code,
                    "corpName": name,
                    "rows": df.height,
                    "yearFrom": years[0] if years else None,
                    "yearTo": years[-1] if years else None,
                    "nDocs": nDocs,
                }
            )
            progress.advance(_task)

    return pl.DataFrame(records)


def updateEdgarListedUniverse(*, force: bool = False) -> Path:
    """SEC exchange ticker 원본으로 listed universe 캐시 갱신."""
    from dartlab.core.dataLoaderUniverse import updateEdgarListedUniverse as _impl

    return _impl(
        force=force,
        dataRoot=_getDataRoot(),
        ttlHours=_EDGAR_UNIVERSE_TTL_HOURS,
        listedUniverseUrl=EDGAR_LISTED_UNIVERSE_URL,
        fetchJson=_fetchJson,
        isLocalCacheExpired=_isLocalCacheExpired,
    )


def loadEdgarListedUniverse(*, forceUpdate: bool = False) -> pl.DataFrame:
    """현재 상장 universe 캐시 로드. 필요 시 SEC 원본에서 갱신."""
    path = updateEdgarListedUniverse(force=forceUpdate)
    return pl.read_parquet(path)


def loadEdgarTargetUniverse(tier: str = "all") -> pl.DataFrame:
    """tier별 EDGAR 상장사 목록 반환.

    Parameters
    ----------
    tier : str
        "all" — Nasdaq + NYSE + CBOE (OTC 제외)
        "nasdaq" — Nasdaq만
        "nyse" — NYSE만
        "sp500" — S&P 500 구성 종목 (정적 목록 교차)

    Returns
    -------
    pl.DataFrame
        cik, ticker, title, exchange 컬럼.
    """
    from dartlab.core.dataLoaderUniverse import loadEdgarTargetUniverse as _impl

    return _impl(loadEdgarListedUniverse(), tier, _loadSp500Tickers())


def _loadSp500Tickers() -> list[str] | None:
    """정적 S&P 500 ticker 목록 로드 (edgarTickers.json fallback)."""
    from dartlab.core.dataLoaderUniverse import loadSp500Tickers

    return loadSp500Tickers(Path(__file__).resolve().parents[3])


def extractCorpName(df: pl.DataFrame) -> str | None:
    """DataFrame에서 기업명 추출."""
    for col in ("corp_name", "company_name"):
        if col in df.columns:
            names = [name for name in df[col].unique().to_list() if name]
            if names:
                return names[0]
    return None


def _docIdColumn(df: pl.DataFrame) -> str | None:
    for col in ("rcept_no", "accession_no"):
        if col in df.columns:
            return col
    return None


def _isLocalCacheExpired(path: Path, ttlHours: int) -> bool:
    if not path.exists():
        return True
    ageSeconds = time.time() - path.stat().st_mtime
    return ageSeconds > ttlHours * 3600


def _fetchJson(url: str) -> dict:
    with _socketTimeout():
        request = Request(url, headers=_SEC_HEADERS)
        with urlopen(request) as resp:
            return json.loads(resp.read())


# ── 메모리 최적화 + docs 표준화 ────────────────────────────────────


def _optimizeMemory(df: pl.DataFrame) -> pl.DataFrame:
    """Categorical 전환 + Int 다운캐스트로 메모리 절감."""
    from dartlab.core.dataLoaderNormalize import optimizeMemory

    return optimizeMemory(df)


def _normalizeLoadedFrame(df: pl.DataFrame, category: str) -> pl.DataFrame:
    from dartlab.core.dataLoaderNormalize import normalizeLoadedFrame

    return normalizeLoadedFrame(df, category)


def _normalizeDartDocs(df: pl.DataFrame) -> pl.DataFrame:
    from dartlab.core.dataLoaderNormalize import normalizeDartDocs

    return normalizeDartDocs(df)


def _normalizeEdgarDocs(df: pl.DataFrame) -> pl.DataFrame:
    from dartlab.core.dataLoaderNormalize import normalizeEdgarDocs

    return normalizeEdgarDocs(df)


def _edgarReportTypeFromRow(row: dict) -> str | None:
    from dartlab.core.dataLoaderNormalize import edgarReportTypeFromRow

    return edgarReportTypeFromRow(row)


def _applyEdgarPeriodKeys(df: pl.DataFrame) -> pl.DataFrame:
    from dartlab.core.dataLoaderNormalize import applyEdgarPeriodKeys

    return applyEdgarPeriodKeys(df)


def _inferEdgarPeriodKeyMap(filings: list[dict]) -> dict[str, str | None]:
    from dartlab.core.dataLoaderNormalize import inferEdgarPeriodKeyMap

    return inferEdgarPeriodKeyMap(filings)


# ── Pyodide (emscripten) 전용 경로 ──────────────────────────────────


def _loadDataPyodide(
    stockCode: str,
    category: str,
    *,
    sinceYear: int | None = None,
    columns: list[str] | None = None,
) -> pl.DataFrame:
    """Pyodide 환경: pre-fetched FS 파일 → pyarrow → polars.

    JS 측에서 HF parquet을 fetch → pyodide FS에 미리 기록.
    Python은 로컬 파일처럼 pyarrow로 읽는다.
    polars WASM wheel은 read_parquet 비활성이므로 pyarrow 경유.
    """
    from dartlab.core.dataLoaderPyodide import loadDataPyodide

    return loadDataPyodide(stockCode, category, sinceYear=sinceYear, columns=columns)


def _pyodideFetchScanLite() -> None:
    """Pyodide: scan 경량 프리빌드(`finance-lite.parquet`, ~18MB) 만 받아 FS에 저장.

    `huggingface_hub.snapshot_download` 는 pyodide 에 설치되지 않고, 전체 프리빌드
    (307MB finance + report 12개 등) 를 브라우저에서 받기엔 부담이므로 스캔 카테고리의
    경량본 1 파일만 선별 수신한다. 실패 시 명시적 에러를 emit 하여 fallback 이 조용히
    부분 결과를 돌려주는 상황을 차단한다.
    """
    from dartlab.core.dataLoaderPyodide import pyodideFetchScanLite

    pyodideFetchScanLite(_dataDir)


def _pyodideFetchToFS(stockCode: str, category: str, dirPath: str, path: Path) -> None:
    """Pyodide: HF에서 parquet을 fetch하여 FS에 저장.

    여러 pyodide 환경(브라우저/xlwings lite/JupyterLite/Node)을 지원하기 위해
    3가지 방법을 순차 시도한다.
    """
    from dartlab.core.dataLoaderPyodide import pyodideFetchToFS

    pyodideFetchToFS(stockCode, category, dirPath, path)
