"""KRX/KIND/DART 상장법인 등록부 — 종목코드 ↔ 회사명 lookup + 캐시 SSOT.

세 소스의 list fetch + 24h TTL 캐시 (메모리 + parquet) + Protocol DIP 등록을
한 곳에 모은다. 자모 분해·fuzzy 검색은 `fuzzy.py` 자매 모듈.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx
import polars as pl

log = logging.getLogger(__name__)


def _cacheFile() -> Path:
    """KIND 상장법인 캐시 파일 경로 반환.

    Returns
    -------
    Path
        ``{dataRoot}/kindList/corpList.parquet`` 경로.
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "kindList" / "corpList.parquet"


def _krxCacheFile() -> Path:
    """KRX 상장법인 캐시 파일 경로 반환.

    Returns
    -------
    Path
        ``{dataRoot}/krxList/corpList.parquet`` 경로.
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "krxList" / "corpList.parquet"


CACHE_TTL = 86400

KIND_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
KIND_DATA = {
    "method": "download",
    "searchType": "13",
    "fiscalYearEnd": "all",
    "location": "all",
}

_memory: pl.DataFrame | None = None
_memoryTs: float = 0.0
_memoryLock = threading.Lock()


class _TableParser(HTMLParser):
    """KRX KIND HTML 테이블 → 2차원 리스트 변환.

    KIND에서 반환하는 EUC-KR 인코딩 HTML 테이블을 파싱하여
    ``list[list[str]]`` (행 × 열) 형태로 변환한다.

    Attributes
    ----------
    _rows : list[list[str]]
        파싱 완료된 전체 행 목록.
    """

    def __init__(self):
        super().__init__()
        self._inTable = False
        self._inTr = False
        self._inCell = False
        self._rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell = ""

    def handle_starttag(self, tag: str, _attrs):
        """HTML 여는 태그 처리 (stdlib HTMLParser hook).

        Args:
            tag: 태그 이름 (소문자).
            _attrs: 태그 속성 리스트 — 본 파서에서 사용 안 함.

        Returns:
            None — 내부 상태만 갱신.

        Raises:
            없음.

        Example:
            stdlib HTMLParser 의 콜백 — 사용자는 ``parser.feed(html)`` 만 호출.
        """
        if tag == "table":
            self._inTable = True
        elif tag == "tr" and self._inTable:
            self._inTr = True
            self._row = []
        elif tag in ("td", "th") and self._inTr:
            self._inCell = True
            self._cell = ""

    def handle_endtag(self, tag: str):
        """HTML 닫는 태그 처리 (stdlib HTMLParser hook).

        Args:
            tag: 태그 이름 (소문자).

        Returns:
            None — 내부 상태만 갱신.

        Raises:
            없음.

        Example:
            stdlib HTMLParser 의 콜백 — 사용자는 ``parser.feed(html)`` 만 호출.
        """
        if tag in ("td", "th") and self._inCell:
            self._inCell = False
            self._row.append(self._cell.strip())
        elif tag == "tr" and self._inTr:
            self._inTr = False
            if self._row:
                self._rows.append(self._row)
        elif tag == "table":
            self._inTable = False

    def handle_data(self, data: str):
        """HTML 텍스트 데이터 처리 (stdlib HTMLParser hook).

        Args:
            data: 태그 사이의 텍스트.

        Returns:
            None — 내부 cell 버퍼에 누적.

        Raises:
            없음.

        Example:
            stdlib HTMLParser 의 콜백 — 사용자는 ``parser.feed(html)`` 만 호출.
        """
        if self._inCell:
            self._cell += data


def _fetchKind() -> pl.DataFrame:
    """KRX KIND API에서 상장법인 목록 HTML 수집 → DataFrame 변환.

    SPAC·리츠 제외, 6자리 종목코드만 포함.
    네트워크 실패 시 빈 DataFrame 반환.

    Returns
    -------
    pl.DataFrame
        종목코드 : str — 6자리 종목코드
        회사명 : str — 법인명
        업종 : str — 업종명
        주요제품 : str — 주요 제품
        상장일 : str — 상장일
        결산월 : str — 결산월
        대표자명 : str — 대표자명
    """
    try:
        r = httpx.post(KIND_URL, data=KIND_DATA, timeout=30)
    except (httpx.ConnectError, httpx.TimeoutException):
        return pl.DataFrame(schema={"종목코드": pl.Utf8, "회사명": pl.Utf8})
    html = r.content.decode("euc-kr", errors="replace")

    parser = _TableParser()
    parser.feed(html)
    rows = parser._rows
    if len(rows) < 2:
        return pl.DataFrame(schema={"종목코드": pl.Utf8, "회사명": pl.Utf8})

    header = rows[0]
    data = rows[1:]
    records = [dict(zip(header, r)) for r in data if len(r) == len(header)]
    df = pl.DataFrame(records)

    if "종목코드" not in df.columns:
        return pl.DataFrame(schema={"종목코드": pl.Utf8, "회사명": pl.Utf8})

    df = df.with_columns(pl.col("종목코드").cast(pl.Utf8).str.zfill(6))
    df = df.filter(pl.col("종목코드").str.contains(r"^[0-9A-Z]{6}$"))
    df = df.filter(~pl.col("회사명").str.contains(r"스팩|리츠"))
    df = df.unique(subset=["종목코드"]).sort("종목코드")
    return df


def _loadCache() -> pl.DataFrame | None:
    """KIND 파일 캐시 로드. TTL(24h) 초과 또는 Pyodide면 None.

    Returns
    -------
    pl.DataFrame | None
        캐시된 상장법인 DataFrame. 없거나 만료 시 None.
    """
    import sys

    if sys.platform == "emscripten":
        return None  # Pyodide: 로컬 캐시 없음
    path = _cacheFile()
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        return None
    return pl.read_parquet(str(path))


def _saveCache(df: pl.DataFrame) -> None:
    """KIND 상장법인 DataFrame을 Parquet 파일로 캐시 저장.

    Pyodide 환경에서는 저장하지 않는다 (영속 FS 없음).

    Parameters
    ----------
    df : pl.DataFrame
        저장할 상장법인 DataFrame.
    """
    import sys

    if sys.platform == "emscripten":
        return  # Pyodide: write_parquet 비활성 + 영속 FS 없음
    path = _cacheFile()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(path))


def getKindList(*, forceRefresh: bool = False) -> pl.DataFrame:
    """KRX KIND 상장법인 전체 목록.

    캐시 우선순위: 메모리 → 파일(24h TTL) → KIND API.
    SPAC·리츠 제외, 6자리 종목코드만 포함.

    Parameters
    ----------
    forceRefresh : bool
        True면 캐시 무시하고 KIND API 재요청. 기본 False.

    Returns
    -------
    pl.DataFrame
        종목코드 : str — 6자리 종목코드
        회사명 : str — 법인명
        업종 : str — 업종명
        주요제품 : str — 주요 제품
        상장일 : str — 상장일
        결산월 : str — 결산월
        대표자명 : str — 대표자명

    Raises
    ------
    없음
        KIND fetch 실패 시 빈 DataFrame 반환 (예외 흡수).

    Example
    -------
    >>> df = getKindList()
    """
    global _memory, _memoryTs

    import sys

    if sys.platform == "emscripten":
        # Pyodide: KRX API CORS 차단 → 빈 DataFrame (corpName은 docs에서 추출)
        if _memory is None:
            _memory = pl.DataFrame({"회사명": [], "종목코드": []})
        return _memory

    if not forceRefresh and _memory is not None:
        if (time.time() - _memoryTs) < CACHE_TTL:
            return _memory

    with _memoryLock:
        # double-check
        if not forceRefresh and _memory is not None:
            if (time.time() - _memoryTs) < CACHE_TTL:
                return _memory

        if not forceRefresh:
            cached = _loadCache()
            if cached is not None:
                _memory = cached
                _memoryTs = time.time()
                _invalidateSearchCache()
                return cached

        from dartlab.core.messaging import emit

        emit("listing:download")
        df = _fetchKind()
        _saveCache(df)
        _memory = df
        _memoryTs = time.time()
        _invalidateSearchCache()
        emit("listing:done", count=df.height)
        return df


def _invalidateSearchCache() -> None:
    """getKindList 갱신 시 fuzzy module 의 검색 캐시 무효화."""
    try:
        from . import fuzzy

        fuzzy._searchCache = None
    except ImportError:
        pass


def codeToName(stockCode: str) -> str | None:
    """종목코드 → 회사명.

    Parameters
    ----------
    stockCode : str
        6자리 종목코드.

    Returns
    -------
    str | None
        회사명. 못 찾으면 None.

    Raises
    ------
    없음
        ``getKindList()`` 가 빈 DataFrame 반환 시 None.

    Example
    -------
    >>> codeToName("005930")
    '삼성전자'
    """
    df = getKindList()
    match = df.filter(pl.col("종목코드") == stockCode)
    if match.height == 0:
        return None
    return match["회사명"][0]


def nameToCode(corpName: str) -> str | None:
    """회사명 → 종목코드. 정확히 일치하는 첫 번째 결과.

    Parameters
    ----------
    corpName : str
        회사명.

    Returns
    -------
    str | None
        6자리 종목코드. 못 찾으면 None.

    Raises
    ------
    없음
        ``getKindList()`` 가 빈 DataFrame 반환 시 None.

    Example
    -------
    >>> nameToCode("삼성전자")
    '005930'
    """
    df = getKindList()
    match = df.filter(pl.col("회사명") == corpName)
    if match.height == 0:
        return None
    return match["종목코드"][0]


# ── DART 전체 법인 목록 (OpenDART CORPCODE.xml) ───────────────────


def _dartListCacheFile() -> Path:
    """OpenDART 법인 목록 캐시 파일 경로 반환.

    Returns
    -------
    Path
        ``{dataRoot}/dartList/dartList.parquet`` 경로.
    """
    from dartlab.core.dataLoader import _getDataRoot

    return _getDataRoot() / "dartList" / "dartList.parquet"


_dartMemory: pl.DataFrame | None = None
_dartMemoryTs: float = 0.0
_dartMemoryLock = threading.Lock()


def _loadDartListFromHf() -> pl.DataFrame | None:
    """HuggingFace에서 dartList.parquet 다운로드.

    ``eddmpython/dartlab-data`` 데이터셋에서 ``metadata/dartList.parquet`` 를 가져온다.
    huggingface_hub 미설치 또는 네트워크 실패 시 None.

    Returns
    -------
    pl.DataFrame | None
        corp_code : str — DART 고유 법인코드 (8자리)
        corp_name : str — 법인명
        stock_code : str — 종목코드 (6자리, 비상장은 빈 문자열)
        modify_date : str — 최종 수정일
    """
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(
            repo_id="eddmpython/dartlab-data",
            repo_type="dataset",
            filename="metadata/dartList.parquet",
        )
        return pl.read_parquet(path)
    except (ImportError, OSError, ValueError, KeyError):
        return None


def getDartList(*, forceRefresh: bool = False) -> pl.DataFrame:
    """OpenDART 전체 법인 목록 (corp_code 8자리 매핑 포함).

    캐시 우선순위: 메모리 → 파일(24h TTL) → HuggingFace.
    DART API 키 불필요 — HuggingFace에서 자동 다운로드.

    Args:
        forceRefresh: True면 캐시 무시하고 HF에서 새로 다운로드.

    Returns:
        DataFrame (corp_code, corp_name, stock_code, modify_date).

    Raises:
        없음 — HF 다운로드 실패 시 캐시 fallback 또는 빈 DataFrame.

    Example:
        >>> df = getDartList()
    """
    global _dartMemory, _dartMemoryTs

    if not forceRefresh and _dartMemory is not None:
        if (time.time() - _dartMemoryTs) < CACHE_TTL:
            return _dartMemory

    with _dartMemoryLock:
        if not forceRefresh and _dartMemory is not None:
            if (time.time() - _dartMemoryTs) < CACHE_TTL:
                return _dartMemory

        cacheFile = _dartListCacheFile()
        if not forceRefresh and cacheFile.exists():
            age = time.time() - cacheFile.stat().st_mtime
            if age < CACHE_TTL:
                _dartMemory = pl.read_parquet(str(cacheFile))
                _dartMemoryTs = time.time()
                return _dartMemory

        from dartlab.core.messaging import emit

        emit("listing:dartlist:download")
        df = _loadDartListFromHf()
        if df is None or df.height == 0:
            log.warning("dartList HF 다운로드 실패")
            if cacheFile.exists():
                _dartMemory = pl.read_parquet(str(cacheFile))
                _dartMemoryTs = time.time()
                return _dartMemory
            return pl.DataFrame(
                schema={"corp_code": pl.Utf8, "corp_name": pl.Utf8, "stock_code": pl.Utf8, "modify_date": pl.Utf8}
            )

        cacheFile.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(str(cacheFile))
        _dartMemory = df
        _dartMemoryTs = time.time()
        emit("listing:dartlist:done", count=df.height)
        return df


# ── KRX data.krx.co.kr 상장법인 목록 ──────────────────────────────


_KRX_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
_KRX_DATA = {
    "locale": "ko_KR",
    "mktsel": "ALL",
    "typeNo": "0",
    "searchText": "",
    "bld": "dbms/comm/finder/finder_stkisu",
}
_KRX_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101",
}

_krxMemory: pl.DataFrame | None = None
_krxMemoryTs: float = 0.0
_krxMemoryLock = threading.Lock()


def _fetchKrx() -> pl.DataFrame:
    """KRX data.krx.co.kr JSON API에서 상장법인 목록 수집.

    네트워크 실패·HTTP 오류·JSON 파싱 실패 시 빈 DataFrame 반환.

    Returns
    -------
    pl.DataFrame
        full_code : str — ISIN 전체 코드 (12자리)
        short_code : str — 단축 종목코드 (6자리)
        codeName : str — 종목명
        marketName : str — 시장구분 (KOSPI/KOSDAQ/KONEX)
    """
    schema = {
        "full_code": pl.Utf8,
        "short_code": pl.Utf8,
        "codeName": pl.Utf8,
        "marketName": pl.Utf8,
    }
    try:
        r = httpx.post(
            _KRX_URL,
            data=_KRX_DATA,
            headers=_KRX_HEADERS,
            timeout=30,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        log.warning("KRX 상장법인 목록 수집 실패: %s", exc)
        return pl.DataFrame(schema=schema)

    if r.status_code != 200:
        log.warning("KRX 상장법인 목록 HTTP %d", r.status_code)
        return pl.DataFrame(schema=schema)

    try:
        jo = json.loads(r.text)
    except (json.JSONDecodeError, ValueError) as exc:
        log.warning("KRX 응답 JSON 파싱 실패: %s", exc)
        return pl.DataFrame(schema=schema)

    block = jo.get("block1", [])
    if not block:
        log.warning("KRX 응답에 block1 데이터 없음")
        return pl.DataFrame(schema=schema)

    df = pl.DataFrame(block)
    return df


def _loadKrxCache() -> pl.DataFrame | None:
    """KRX 파일 캐시 로드. TTL(24h) 초과면 None.

    Returns
    -------
    pl.DataFrame | None
        캐시된 KRX 상장법인 DataFrame. 없거나 만료 시 None.
    """
    path = _krxCacheFile()
    if not path.exists():
        return None
    age = time.time() - path.stat().st_mtime
    if age > CACHE_TTL:
        return None
    return pl.read_parquet(str(path))


def _saveKrxCache(df: pl.DataFrame) -> None:
    """KRX 상장법인 DataFrame을 Parquet 파일로 캐시 저장.

    Parameters
    ----------
    df : pl.DataFrame
        저장할 KRX 상장법인 DataFrame.
    """
    path = _krxCacheFile()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(str(path))


def getKrxList(*, forceRefresh: bool = False) -> pl.DataFrame:
    """KRX data.krx.co.kr 상장법인 전체 목록.

    캐시 우선순위: 메모리 -> 파일(24h TTL) -> KRX API.
    KIND 목록보다 상세 컬럼(full_code, short_code, marketName 등) 제공.

    Parameters
    ----------
    forceRefresh : bool
        True면 캐시 무시하고 KRX API 재요청. 기본 False.

    Returns
    -------
    pl.DataFrame
        full_code : str — ISIN 전체 코드 (12자리)
        short_code : str — 단축 종목코드 (6자리)
        codeName : str — 종목명
        marketName : str — 시장구분 (KOSPI/KOSDAQ/KONEX)

    Raises
    ------
    없음
        KRX API 실패 시 빈 DataFrame 반환 (예외 흡수).

    Example
    -------
    >>> df = getKrxList()
    """
    global _krxMemory, _krxMemoryTs

    if not forceRefresh and _krxMemory is not None:
        if (time.time() - _krxMemoryTs) < CACHE_TTL:
            return _krxMemory

    with _krxMemoryLock:
        if not forceRefresh and _krxMemory is not None:
            if (time.time() - _krxMemoryTs) < CACHE_TTL:
                return _krxMemory

        if not forceRefresh:
            cached = _loadKrxCache()
            if cached is not None:
                _krxMemory = cached
                _krxMemoryTs = time.time()
                return cached

        from dartlab.core.messaging import emit

        emit("listing:krx:download")
        df = _fetchKrx()
        if df.height > 0:
            _saveKrxCache(df)
        _krxMemory = df
        _krxMemoryTs = time.time()
        emit("listing:krx:done", count=df.height)
        return df


# ── ListingResolver 구현 + register (정공법 B — DIP) ─────────────


class GatherListingResolver:
    """ListingResolver 구현 — core/resolve.py + providers/dart/Company 가 이 인스턴스 사용 (registry 경유).

    core/providers 가 gather/listing.py 직접 import 안 함. module load 시점에 register.
    """

    def search(self, query: str, *, limit: int | None = None) -> pl.DataFrame | None:
        """회사명 검색 — searchName 위임.

        Parameters
        ----------
        query : str
            검색어.
        limit : int | None
            반환 행수 상한 (가장 관련도 높은 N). None이면 전체.

        Returns
        -------
        pl.DataFrame | None
            매칭된 종목 DataFrame. 위임 실패 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.search("삼성", limit=10)
        """
        try:
            from .fuzzy import searchName

            return searchName(query, limit=limit)
        except (ValueError, OSError):
            return None

    def fuzzy(self, query: str, *, maxResults: int = 5) -> pl.DataFrame | None:
        """fuzzy 검색 — fuzzySearch 위임.

        Parameters
        ----------
        query : str
            검색어 (한글/영문/초성).
        maxResults : int
            최대 결과 수. 기본 5.

        Returns
        -------
        pl.DataFrame | None
            관련도 순 매칭 DataFrame. 위임 실패 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.fuzzy("삼전", maxResults=5)
        """
        try:
            from .fuzzy import fuzzySearch

            return fuzzySearch(query, maxResults=maxResults)
        except (ValueError, OSError):
            return None

    def codeToName(self, stockCode: str) -> str | None:
        """stockCode → 회사명 변환.

        Parameters
        ----------
        stockCode : str
            6자리 종목코드.

        Returns
        -------
        str | None
            회사명. 위임 실패 또는 미존재 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> r.codeToName("005930")
        """
        try:
            return codeToName(stockCode)
        except (ValueError, OSError):
            return None

    def nameToCode(self, corpName: str) -> str | None:
        """회사명 → stockCode 변환.

        Parameters
        ----------
        corpName : str
            회사명 (정확한 매칭).

        Returns
        -------
        str | None
            6자리 종목코드. 위임 실패 또는 미존재 시 None.

        Raises
        ------
        없음
            ValueError/OSError 는 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> r.nameToCode("삼성전자")
        """
        try:
            return nameToCode(corpName)
        except (ValueError, OSError):
            return None

    def kindList(self, *, forceRefresh: bool = False) -> pl.DataFrame:
        """KIND 상장법인 목록.

        Parameters
        ----------
        forceRefresh : bool
            True면 캐시 무시 재요청.

        Returns
        -------
        pl.DataFrame
            전체 상장법인 목록 — getKindList 와 동일 스키마.

        Raises
        ------
        없음
            getKindList 가 내부에서 흡수.

        Example
        -------
        >>> r = GatherListingResolver()
        >>> df = r.kindList()
        """
        return getKindList(forceRefresh=forceRefresh)


def _registerGatherListingResolver() -> None:
    """import 시점 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.listingResolver import registerListingResolver

    registerListingResolver(GatherListingResolver())


_registerGatherListingResolver()
