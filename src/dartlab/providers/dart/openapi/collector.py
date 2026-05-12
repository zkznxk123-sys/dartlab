"""DART 공시문서 수집기 — eddmpython DartDocs.py 포팅.

프록시 없이 httpx 기반 동기 크롤링.
DartClient를 재사용하여 API 키 관리를 openapi 체계에 통합.

사용법::

    from dartlab.providers.dart.openapi.collector import DocsCollector

    collector = DocsCollector("005930")
    collector.collect(quarters=8)

    # 여러 종목
    from dartlab.providers.dart.openapi.collector import collectMultiple
    collectMultiple(["005930", "000660"], quarters=8)

CLI::

    dartlab collect 005930
    dartlab collect 005930 --quarters 12
    dartlab collect --stats
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from pathlib import Path

import httpx
import polars as pl

from dartlab import config as _cfg
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger
from dartlab.providers.dart.openapi.client import DartClient
from dartlab.providers.dart.openapi.corpCode import findCorpCode, loadCorpCodes
from dartlab.providers.dart.openapi.disclosure import listFilings

_log = getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────

_MIN_CONTENT_LENGTH = 50
_REQUEST_TIMEOUT = 30

# viewer 페이지 파싱 헬퍼는 providers/dart/viewerPageExtractor SSOT 사용.
# gather/dart/viewer (key 무관) 와 본 collector (key 기반 bulk) 양쪽이 import.
from dartlab.providers.dart.parse.viewerPageExtractor import (  # noqa: E402
    DART_MAIN_BASE as _DART_MAIN_BASE,
)
from dartlab.providers.dart.parse.viewerPageExtractor import (
    htmlToText as _htmlToText,
)
from dartlab.providers.dart.parse.viewerPageExtractor import (
    parseSubDocs as _parseSubDocs,
)

# ── HTTP 세션 ────────────────────────────────────


def _makeSession() -> httpx.Client:
    """크롤링용 세션."""
    return httpx.Client(
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        },
        follow_redirects=True,
    )


# ── 수집기 클래스 ─────────────────────────────────────


class DocsCollector:
    """DART 공시문서 수집기.

    Parameters
    ----------
    stockCode : str
        종목코드 (6자리).
    client : DartClient | None
        기존 클라이언트 재사용. None이면 새로 생성 (환경변수에서 API 키 탐색).
    """

    def __init__(self, stockCode: str, *, client: DartClient | None = None):
        self.stockCode = stockCode
        self._client = client or DartClient()
        self._corpCode = findCorpCode(self._client, stockCode)
        if self._corpCode is None:
            raise ValueError(f"종목코드 '{stockCode}'에 해당하는 corp_code를 찾을 수 없습니다")

        # corp_name 조회
        codes = loadCorpCodes(self._client)
        match = codes.filter(pl.col("stock_code") == stockCode)
        self.corpName = match["corp_name"][0] if match.height > 0 else stockCode

        self._dataDir = _resolveDataDir()
        self._parquetPath = self._dataDir / f"{stockCode}.parquet"
        self._existingReports: set[str] = set()
        self._loadExisting()

    def _loadExisting(self) -> None:
        """기존 parquet에서 이미 수집된 rcept_no 세트 로드."""
        if self._parquetPath.exists():
            try:
                df = pl.scan_parquet(self._parquetPath).select("rcept_no").collect(engine="streaming")
                self._existingReports = set(df["rcept_no"].unique().to_list())
            except (pl.exceptions.ComputeError, OSError):
                self._existingReports = set()

    def _getFilingList(
        self,
        *,
        quarters: int = 8,
        includeQuarterly: bool = True,
    ) -> pl.DataFrame:
        """수집 대상 공시 목록 조회."""
        years = (quarters + 3) // 4
        startYear = datetime.now().year - years
        start = f"{startYear}0101"

        filings = listFilings(
            self._client,
            self.stockCode,
            start=start,
            filingType="A",
            fetchAll=True,
        )

        if filings.is_empty():
            return filings

        if not includeQuarterly:
            annualKw = ["사업보고서", "연결재무제표"]
            quarterKw = ["분기", "반기"]
            mask = pl.lit(False)
            for kw in annualKw:
                mask = mask | pl.col("report_nm").str.contains(kw, literal=True)
            qMask = pl.lit(False)
            for kw in quarterKw:
                qMask = qMask | pl.col("report_nm").str.contains(kw, literal=True)
            filings = filings.filter(mask & ~qMask)

        if self._existingReports:
            filings = filings.filter(~pl.col("rcept_no").is_in(list(self._existingReports)))

        return filings

    def _appendSections(self, newSections: list[dict]) -> int:
        """새 섹션을 parquet에 추가 (원자적 교체)."""
        newDf = pl.DataFrame(newSections)

        if self._parquetPath.exists():
            existingDf = pl.read_parquet(self._parquetPath)
            combinedDf = pl.concat([existingDf, newDf])
        else:
            combinedDf = newDf

        tmpPath = self._parquetPath.with_suffix(".parquet.tmp")
        combinedDf.write_parquet(tmpPath)

        if self._parquetPath.exists():
            self._parquetPath.unlink()
        tmpPath.rename(self._parquetPath)

        return len(newSections)

    def collect(
        self,
        *,
        quarters: int = 8,
        includeQuarterly: bool = True,
        minDelay: float = 5.0,
        maxDelay: float = 10.0,
    ) -> int:
        """공시문서 수집 (동기 — httpx 기반 순차 크롤링).

        Parameters
        ----------
        quarters : int
            최근 분기 수 (기본 8 = 2년치).
        includeQuarterly : bool
            분기/반기보고서 포함 여부.
        minDelay : float
            요청 간 최소 대기 초.
        maxDelay : float
            요청 간 최대 대기 초.

        Returns
        -------
        int
            저장된 섹션 수.

        Raises:
            없음.

        Example:
            >>> collect(...)
        """
        filings = self._getFilingList(
            quarters=quarters,
            includeQuarterly=includeQuarterly,
        )

        if filings.is_empty():
            _log.info("수집할 문서 없음: %s", self.corpName)
            return 0

        _log.info("수집 대상: %d건 (%s)", filings.height, self.corpName)

        rceptNos = filings["rcept_no"].to_list()
        rceptDates = filings["rcept_dt"].to_list()
        reportNames = filings["report_nm"].to_list()
        corpNames = (
            filings["corp_name"].to_list() if "corp_name" in filings.columns else [self.corpName] * len(rceptNos)
        )

        from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

        session = _makeSession()

        # Phase 1: 하위 섹션 URL 수집
        allSubDocs: list[dict] = []
        failCount1 = 0

        _p1 = Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(), MofNCompleteColumn())
        _t1 = _p1.add_task(f"[1/2] 목차 수집 | {self.corpName}", total=len(rceptNos))
        with _p1:
            for i, rcpNo in enumerate(rceptNos):
                _p1.update(_t1, description=f"[1/2] 목차 | {reportNames[i]}")
                url = f"{_DART_MAIN_BASE}?rcpNo={rcpNo}"
                try:
                    resp = session.get(url, timeout=_REQUEST_TIMEOUT)
                    resp.raise_for_status()
                    subDocs = _parseSubDocs(resp.text, rcpNo)
                    for sd in subDocs:
                        sd["rcept_date"] = rceptDates[i]
                        sd["report_type"] = reportNames[i]
                        sd["corp_name"] = corpNames[i]
                    allSubDocs.extend(subDocs)
                    _p1.update(_t1, description=f"[1/2] 목차 | {reportNames[i]} → {len(subDocs)}개")
                except httpx.HTTPError:
                    failCount1 += 1
                    _p1.update(_t1, description=f"[1/2] 목차 | {reportNames[i]} 실패")

                _p1.advance(_t1)
                if i < len(rceptNos) - 1:
                    time.sleep(random.uniform(minDelay, maxDelay))

        if failCount1:
            _log.warning("  목차 수집 실패: %d건", failCount1)

        if not allSubDocs:
            _log.info("하위문서 없음")
            return 0

        # Phase 2: HTML 수집 및 텍스트 변환
        uniqueUrls = []
        seen: set[str] = set()
        for sd in allSubDocs:
            if sd["url"] not in seen:
                uniqueUrls.append(sd["url"])
                seen.add(sd["url"])

        uniqueReports = len(set(sd["rcept_no"] for sd in allSubDocs))
        urlToHtml: dict[str, str] = {}
        failCount2 = 0

        # url → 섹션 제목 매핑
        urlToTitle: dict[str, str] = {}
        for sd in allSubDocs:
            if sd["url"] not in urlToTitle:
                urlToTitle[sd["url"]] = sd["title"]

        _p2 = Progress(SpinnerColumn(), TextColumn("[bold blue]{task.description}"), BarColumn(), MofNCompleteColumn())
        _t2 = _p2.add_task(
            f"[2/2] HTML 수집 | {self.corpName} ({uniqueReports}건, {len(uniqueUrls)}섹션)", total=len(uniqueUrls)
        )
        with _p2:
            for i, url in enumerate(uniqueUrls):
                title = urlToTitle.get(url, "")
                _p2.update(_t2, description=f"[2/2] HTML | {title[:40]}" if title else "[2/2] HTML")
                try:
                    resp = session.get(url, timeout=_REQUEST_TIMEOUT)
                    resp.raise_for_status()
                    urlToHtml[url] = resp.text
                except httpx.HTTPError:
                    failCount2 += 1

                _p2.advance(_t2)
                if i < len(uniqueUrls) - 1:
                    time.sleep(random.uniform(minDelay, maxDelay))

        if failCount2:
            _log.warning("  HTML 수집 실패: %d건", failCount2)

        # Phase 3: 텍스트 변환 → parquet 저장
        allSections: list[dict] = []
        seenReports: set[str] = set()

        for sd in allSubDocs:
            url = sd["url"]
            if url not in urlToHtml:
                continue

            text = _htmlToText(urlToHtml[url])
            if len(text.strip()) < _MIN_CONTENT_LENGTH:
                continue

            rcpNo = sd["rcept_no"]
            rceptDate = sd["rcept_date"]
            year = rceptDate[:4] if len(rceptDate) >= 4 else "unknown"

            allSections.append(
                {
                    "corp_code": self._corpCode,
                    "corp_name": sd["corp_name"],
                    "stock_code": self.stockCode,
                    "year": year,
                    "rcept_date": rceptDate,
                    "rcept_no": rcpNo,
                    "report_type": sd["report_type"],
                    "section_order": sd["order"],
                    "section_title": sd["title"],
                    "section_url": url,
                    "section_content": text,
                }
            )
            seenReports.add(rcpNo)

        if allSections:
            savedCount = self._appendSections(allSections)
            _log.info("저장 완료: %d개 보고서, %d개 섹션", len(seenReports), savedCount)
            _log.info("파일: %s", self._parquetPath)
            self._loadExisting()
            return savedCount

        _log.info("저장할 섹션 없음")
        return 0


# ── 배치 수집 헬퍼 ────────────────────────────────────


def _resolveDataDir() -> Path:
    """docs 데이터 디렉토리 (dartlab 캐시 경로)."""
    root = Path(_cfg.dataDir)
    d = root / DATA_RELEASES["docs"]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def collectMultiple(
    stockCodes: list[str],
    *,
    quarters: int = 8,
    includeQuarterly: bool = True,
    minDelay: float = 5.0,
    maxDelay: float = 10.0,
    stockDelay: tuple[float, float] = (30.0, 60.0),
    client: DartClient | None = None,
) -> dict[str, int]:
    """여러 종목 순차 수집.

    Returns
    -------
    dict
        {종목코드: 저장된 섹션 수}. 실패 시 -1.

    Raises:
        없음.

    Example:
        >>> collectMultiple(...)
    """
    sharedClient = client or DartClient()
    results: dict[str, int] = {}
    successCount = 0
    failCount = 0

    for i, code in enumerate(stockCodes):
        _log.info("── [%d/%d] %s ──", i + 1, len(stockCodes), code)

        try:
            collector = DocsCollector(code, client=sharedClient)
            count = collector.collect(
                quarters=quarters,
                includeQuarterly=includeQuarterly,
                minDelay=minDelay,
                maxDelay=maxDelay,
            )
            results[code] = count
            if count > 0:
                successCount += 1
        except (ValueError, OSError) as e:
            _log.warning("수집 실패: %s", e)
            results[code] = -1
            failCount += 1

        if i < len(stockCodes) - 1:
            delay = random.uniform(*stockDelay)
            _log.info("다음 종목까지 %.0f초 대기...", delay)
            time.sleep(delay)

    _log.info("전체 완료: 성공 %d / 실패 %d / 총 %d", successCount, failCount, len(stockCodes))
    return results


def listUncollected(*, client: DartClient | None = None, limit: int | None = None) -> list[tuple[str, str]]:
    """아직 수집되지 않은 상장 종목 리스트.

    Args:
        client: DartClient (재사용 시).
        limit: 최대 항목 수. None 이면 무제한.

    Returns:
        ``[(종목코드, 회사명), ...]`` 리스트.

    Example:
        >>> listUncollected(limit=50)

    Raises:
        없음.
    """
    c = client or DartClient()
    codes = loadCorpCodes(c)

    listed = codes.filter(pl.col("stock_code").is_not_null() & (pl.col("stock_code").str.strip_chars() != ""))

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}

    uncollected = listed.filter(~pl.col("stock_code").is_in(list(existing)))
    if limit is not None:
        uncollected = uncollected.head(limit)
    return list(
        zip(
            uncollected["stock_code"].to_list(),
            uncollected["corp_name"].to_list(),
        )
    )


def collectionStats(*, client: DartClient | None = None) -> dict:
    """수집 현황 통계.

    Args:
        client: 인자.

    Raises:
        없음.

    Example:
        >>> collectionStats(...)
    """
    c = client or DartClient()
    codes = loadCorpCodes(c)

    listed = codes.filter(pl.col("stock_code").is_not_null() & (pl.col("stock_code").str.strip_chars() != ""))

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}
    collected = listed.filter(pl.col("stock_code").is_in(list(existing)))

    return {
        "totalListed": listed.height,
        "collected": collected.height,
        "uncollected": listed.height - collected.height,
    }


def listUncollectedKind(
    *,
    limit: int | None = None,
) -> list[tuple[str, str]]:
    """KRX KIND 기준 미수집 상장 종목 리스트.

    corp_code API 없이도 동작 (KIND HTML만 사용).

    Parameters
    ----------
    limit : int | None
        최대 개수. None이면 전체.

    Returns
    -------
    list
        [(종목코드, 회사명), ...]

    Raises:
        없음.

    Example:
        >>> listUncollectedKind(...)
    """
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        return []
    kindDf = resolver.kindList()
    # 코넥스 제외, 종목코드 6자리 (영문자 포함 코드도 허용: 0001A0 등)
    kindDf = kindDf.filter(pl.col("시장구분") != "코넥스")
    kindDf = kindDf.filter(pl.col("종목코드").str.len_chars() == 6)

    dataDir = _resolveDataDir()
    existing = {f.stem for f in dataDir.glob("*.parquet") if not f.name.startswith(".")}

    uncollected = kindDf.filter(~pl.col("종목코드").is_in(list(existing)))

    result = list(
        zip(
            uncollected["종목코드"].to_list(),
            uncollected["회사명"].to_list(),
        )
    )
    if limit:
        result = result[:limit]
    return result


def iterUncollected(*, client: DartClient | None = None, limit: int | None = None):
    """``listUncollected`` 의 iterator pair (룰 10).

    Args:
        client: DartClient (재사용 시).
        limit: 최대 항목 수. None 이면 무제한.

    Yields:
        ``(종목코드, 회사명)`` 튜플.

    Raises:
        없음.

    Example:
        >>> for code, name in iterUncollected(limit=10):
        ...     print(code, name)
    """
    yield from listUncollected(client=client, limit=limit)


def iterUncollectedKind(*, limit: int | None = None):
    """``listUncollectedKind`` 의 iterator pair (룰 10).

    Args:
        limit: 최대 항목 수. None 이면 무제한.

    Yields:
        ``(종목코드, 회사명)`` 튜플.

    Raises:
        없음 (ListingResolver 부재 시 빈 generator).

    Example:
        >>> for code, name in iterUncollectedKind(limit=10):
        ...     print(code, name)
    """
    yield from listUncollectedKind(limit=limit)
