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

import dartlab.config as _cfg
from dartlab.core.dartClient import DartClient
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger
from dartlab.providers.dart.openapi.corpCode import findCorpCode, loadCorpCodes
from dartlab.providers.dart.openapi.disclosure import listFilings

_log = getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────

_MIN_CONTENT_LENGTH = 50
_REQUEST_TIMEOUT = 30

# viewer 페이지 파싱 헬퍼는 dartlab.core.parse.dartViewerPage SSOT 사용.
# gather/dart/viewer (key 무관) 와 본 collector (key 기반 bulk) 양쪽이 import — L0 공유.
from dartlab.core.parse.dartViewerPage import (  # noqa: E402
    DART_MAIN_BASE as _DART_MAIN_BASE,
)
from dartlab.core.parse.dartViewerPage import (
    htmlToText as _htmlToText,
)
from dartlab.core.parse.dartViewerPage import (
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
        """새 섹션을 parquet 에 추가 (원자적 교체, Phase A — sort + row_group_size 적용)."""
        from dartlab.providers.dart.openapi.saver import writeParquetSorted

        newDf = pl.DataFrame(newSections)

        if self._parquetPath.exists():
            existingDf = pl.read_parquet(self._parquetPath)
            combinedDf = pl.concat([existingDf, newDf])
        else:
            combinedDf = newDf

        writeParquetSorted(combinedDf, self._parquetPath)

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

        Args:
            quarters: 수집 분기 수 (예 8 = 2 년치).
            includeQuarterly: True 면 분기보고서 포함, False 면 사업보고서만.
            minDelay: 최소 호출 간격 (초).
            maxDelay: 최대 호출 간격 (초).

        Returns:
            int — 수집 건수.

        SeeAlso:
            - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

        Requires:
            - dartlab
            - datetime
            - httpx
            - polars
            - random

        Capabilities:
            - DART 정기보고서 docs (사업/분기/반기) ZIP 다운로드 + 분기별 분할.

        Guide:
            - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

        AIContext:
            internal collector — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 다종목 collect → 일 한도 초과. 멀티 키 (DART_API_KEYS) 또는 분산 수집.
                - quarters > 20 호출 시 부담 — DART 5 년 cap.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY + 종목코드.
            Freshness:
                - DART OpenAPI 실시간 (정기보고서 마감 후 30~45 일).
            Dataflow:
                - 종목코드 → DartClient → docs ZIP 다운로드 → HTML→text → parquet.
            TargetMarkets:
                - KR (DART) 정기보고서 수집.
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

        from dartlab.core.logger import getConsole

        session = _makeSession()

        # Phase 1: 하위 섹션 URL 수집
        allSubDocs: list[dict] = []
        failCount1 = 0

        _p1 = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=getConsole(),
        )
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

        _p2 = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=getConsole(),
        )
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

    Args:
        stockCodes: 종목코드 리스트.
        quarters: 수집 분기 수.
        includeQuarterly: True 면 분기보고서 포함.
        minDelay: 최소 호출 간격 (초).
        maxDelay: 최대 호출 간격 (초).
        stockDelay: 종목 간 sleep 구간 (min, max).
        client: DartClient 인스턴스. None 이면 자동 생성.

    Returns:
        dict[str, int] — 종목 별 수집 건수.

    SeeAlso:
        - ``DocsCollector`` 클래스 / ``collectMultiple`` — 본 모듈 entry.

    Requires:
        - dartlab
        - datetime
        - httpx
        - polars
        - random

    Capabilities:
        - DART 정기보고서 docs 수집 + 통계.

    Guide:
        - 운영자 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal collector — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 수집 → 일 한도 초과.
            - quarters > 20 호출 시 부담.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEY + 종목코드.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 → DartClient → docs ZIP → HTML→text → parquet.
        TargetMarkets:
            - KR (DART) 정기보고서.
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


# ── status / iter helper 는 collectorStatus.py 로 분리 (룰 3 LoC).
from dartlab.providers.dart.openapi.collectorStatus import (  # noqa: E402, F401
    collectionStats,
    iterUncollected,
    iterUncollectedKind,
    listUncollected,
    listUncollectedKind,
)
