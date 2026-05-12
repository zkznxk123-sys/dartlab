"""배치 수집 — 병렬 + 증분.

eddmpython v2 DartBase 패턴을 dartlab에 흡수.
키 N개 → asyncio 워커 N개 → Queue 기반 종목 분배.

개별: Dart()("005930").saveFinance(2016)  # 기존 그대로
배치: batchCollect(["005930", "000660"], categories=["finance", "report", "docs"])
전체: batchCollectAll(categories=["finance"])  # 전체 상장종목
"""

from __future__ import annotations

import asyncio
import io
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from dartlab.core.logger import getLogger

_log = getLogger(__name__)


import httpx
import polars as pl

from dartlab.providers.dart.openapi.dartKey import resolveDartKeys

BASE_URL = "https://opendart.fss.or.kr/api"

# ── 상수 ──

from dartlab.providers.dart.openapi.constants import (
    CODE_TO_QUARTER as _CODE_TO_QUARTER,
)
from dartlab.providers.dart.openapi.constants import (
    CODE_TO_QUARTER_KR as _CODE_TO_QUARTER_KR,
)
from dartlab.providers.dart.openapi.constants import KR_TO_API_TYPE as _KR_TO_ENG_API_TYPE
from dartlab.providers.dart.openapi.constants import (
    QUARTER_TO_CODE as _QUARTER_TO_CODE,
)

_PERIODIC_REPORT_CATEGORIES: list[str] = [
    "배당",
    "직원",
    "임원",
    "최대주주",
    "최대주주변동",
    "소액주주",
    "자기주식",
    "증자감자",
    "이사회임원전체보수",
    "이사회임원개인보수",
    "개인별보수",
    "타법인출자",
    "주식총수",
    "회계감사인",
    "감사용역체결",
    "감사비감사계약",
    "사외이사변동",
    "미등기임원보수",
    "회사채미상환",
    "단기사채미상환",
    "공모자금용도",
    "공모자금사용",
    "대주주지분변동",
    "기업어음미상환",
    "채무증권발행실적",
    "조건부자본증권미상환",
    "신종자본증권미상환",
    "이사감사보수총회인정",
    "이사감사보수지급형태",
]

_REPORT_ENDPOINTS: dict[str, str] = {
    "증자감자": "irdsSttus",
    "배당": "alotMatter",
    "자기주식": "tesstkAcqsDspsSttus",
    "최대주주": "hyslrSttus",
    "최대주주변동": "hyslrChgSttus",
    "소액주주": "mrhlSttus",
    "임원": "exctvSttus",
    "직원": "empSttus",
    "이사회임원개인보수": "hmvAuditIndvdlBySttus",
    "이사회임원전체보수": "hmvAuditAllSttus",
    "개인별보수": "indvdlByPay",
    "타법인출자": "otrCprInvstmntSttus",
    "대주주지분변동": "eleStockIstySttus",
    "미등기임원보수": "unrstExctvMendngSttus",
    "주식총수": "stockTotqySttus",
    "회계감사인": "accnutAdtorNmNdAdtOpinion",
    "감사용역체결": "adtServcCnclsSttus",
    "감사비감사계약": "accnutAdtorNonAdtServcCnclsSttus",
    "사외이사변동": "outcmpnyDrctrNdChangeSttus",
    "회사채미상환": "cprndNrdmpBlce",
    "단기사채미상환": "srtpdPsndbtNrdmpBlce",
    "기업어음미상환": "entrprsBilScritsNrdmpBlce",
    "채무증권발행실적": "detScritsIsuAcmslt",
    "조건부자본증권미상환": "cndlCaplScrtsNrdmpBlce",
    "신종자본증권미상환": "newCaplScrtsNrdmpBlce",
    "공모자금용도": "prvsrpCptalUseDtls",
    "공모자금사용": "pssrpCptalUseDtls",
    "이사감사보수총회인정": "drctrAdtAllMendngSttusGmtsckConfmAmount",
    "이사감사보수지급형태": "drctrAdtAllMendngSttusMendngPymntamtTyCl",
}

START_YEAR = 2016


# ── AsyncDartClient ──


class AsyncDartClient:
    """비동기 DART API 클라이언트 (배치 수집 전용)."""

    def __init__(self, apiKey: str, *, requestsPerMinute: int = 580):
        self._key = apiKey
        self._client = httpx.AsyncClient(timeout=30)
        self._minInterval = 60.0 / requestsPerMinute
        self._lastRequest = 0.0
        self.exhausted = False

    async def _throttle(self) -> None:
        """키당 rate limit."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._lastRequest
        if elapsed < self._minInterval:
            await asyncio.sleep(self._minInterval - elapsed)
        self._lastRequest = asyncio.get_event_loop().time()

    async def getJson(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        emptyOn013: bool = False,
    ) -> dict[str, Any] | None:
        """비동기 JSON 요청. 한도 초과 시 None + exhausted=True.

        Args:
            endpoint: 인자.
            params: 인자.
            emptyOn013: 인자.

        Raises:
            없음.

        Example:
            >>> getJson(...)

        Returns:
            dict[str, Any] 또는 None — 결과 dict.

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        await self._throttle()
        merged = {"crtfc_key": self._key}
        if params:
            merged.update(params)
        resp = await self._client.get(f"{BASE_URL}/{endpoint}", params=merged)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "000")
        if status == "000":
            return data
        if status == "013" and emptyOn013:
            return {}
        if status == "020":
            self.exhausted = True
            return None
        return {} if emptyOn013 else None

    async def getDf(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        listKey: str = "list",
    ) -> pl.DataFrame | None:
        """비동기 JSON → DataFrame. 한도 초과 시 None.

        Args:
            endpoint: 인자.
            params: 인자.
            listKey: 인자.

        Raises:
            없음.

        Example:
            >>> getDf(...)

        Returns:
            pl.DataFrame 또는 None — 결과.

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        data = await self.getJson(endpoint, params, emptyOn013=True)
        if data is None:
            return None
        rows = data.get(listKey, [])
        return pl.DataFrame(rows) if rows else pl.DataFrame()

    async def getBytes(self, endpoint: str, params: dict[str, Any] | None = None) -> bytes | None:
        """비동기 바이너리 요청. 한도 초과 시 None.

        Args:
            endpoint: 인자.
            params: 인자.

        Raises:
            없음.

        Example:
            >>> getBytes(...)

        Returns:
            bytes 또는 None — 응답 본문.

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        await self._throttle()
        merged = {"crtfc_key": self._key}
        if params:
            merged.update(params)
        resp = await self._client.get(
            f"{BASE_URL}/{endpoint}",
            params=merged,
            timeout=60,
        )
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct or "text/json" in ct:
            data = resp.json()
            if data.get("status") == "020":
                self.exhausted = True
                return None
        return resp.content

    async def close(self) -> None:
        """HTTP 클라이언트 연결을 닫는다.

        Raises:
            없음.

        Example:
            >>> close(...)

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.
        """
        await self._client.aclose()


# ── 증분 유틸 ──


def _buildAllPeriods(startYear: int = START_YEAR) -> list[tuple[str, str]]:
    """(bsnsYear, reprtCode) 전체 기간 리스트.

    순서: **최신 분기부터 과거 순**.
    이유: DART API 일일 한도(20,000회) ÷ 종목당 ~32회 ≈ ~600 종목/일.
    전체 2,500+ 종목을 매일 처리할 수 없으므로 한도 도달 시 잘리는 종목이 발생한다.
    오래된 분기부터 처리하면 매번 동일한 종목의 **최신 분기**가 잘려서 신규 데이터가
    영구 누락되는 사례가 발생 (2026-04-06 두산에너빌리티 25Q4 누락 388개 사례).
    최신부터 처리하면 한도 잘림이 발생해도 옛날 분기만 잘리고, 신규 분기는 항상 우선
    처리된다.
    """
    endYear = datetime.now().year
    periods = []
    # 역순: 최신 연도 → 과거 연도, 각 연도 안에서도 Q4 → Q1
    for y in range(endYear, startYear - 1, -1):
        for q in ["Q4", "Q3", "Q2", "Q1"]:
            periods.append((str(y), _QUARTER_TO_CODE[q]))
    return periods


def _existingFinancePeriods(path: Path) -> set[tuple[str, str]]:
    """기존 finance parquet에서 수집된 (bsns_year, reprt_code) 세트."""
    if not path.exists():
        return set()
    try:
        schema = pl.read_parquet_schema(path)
        if "bsns_year" not in schema or "reprt_code" not in schema:
            return set()
        df = (
            pl.scan_parquet(path)
            .select("bsns_year", "reprt_code")
            .filter(pl.col("bsns_year").is_not_null() & pl.col("reprt_code").is_not_null())
            .unique()
            .collect(engine="streaming")
        )
        return set(zip(df["bsns_year"].cast(pl.Utf8).to_list(), df["reprt_code"].cast(pl.Utf8).to_list()))
    except (pl.exceptions.ComputeError, pl.exceptions.SchemaError, OSError):
        return set()


def _existingReportPeriods(path: Path) -> set[tuple[str, str, str]]:
    """기존 report parquet에서 수집된 (year, quarter, apiType) 세트."""
    if not path.exists():
        return set()
    try:
        schema = pl.read_parquet_schema(path)
        required = {"year", "quarter", "apiType"}
        if not required.issubset(schema):
            return set()
        df = (
            pl.scan_parquet(path)
            .select("year", "quarter", "apiType")
            .filter(pl.col("year").is_not_null() & pl.col("quarter").is_not_null() & pl.col("apiType").is_not_null())
            .unique()
            .collect(engine="streaming")
        )
        return set(
            zip(
                df["year"].cast(pl.Utf8).to_list(),
                df["quarter"].cast(pl.Utf8).to_list(),
                df["apiType"].cast(pl.Utf8).to_list(),
            )
        )
    except (pl.exceptions.ComputeError, pl.exceptions.SchemaError, OSError, pl.exceptions.ColumnNotFoundError):
        return set()


def _dataPath(category: str, stockCode: str) -> Path:
    """parquet 저장 경로."""
    from dartlab import config as _cfg
    from dartlab.frame.dataConfig import DATA_RELEASES

    subDir = DATA_RELEASES.get(category, {}).get("dir", f"dart/{category}")
    dest = Path(_cfg.dataDir) / subDir / f"{stockCode}.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


# ── 단일 종목 수집 (비동기) ──


async def _collectFinance(
    stockCode: str,
    corpCode: str,
    corpName: str,
    client: AsyncDartClient,
    *,
    incremental: bool = True,
    onPeriod=None,
    targetPeriods: list[tuple[str, str]] | None = None,
) -> int:
    """finance 수집 (CFS+OFS). 반환: 저장된 행 수.

    Args:
        targetPeriods: list.json에서 발견한 정확한 (bsns_year, reprt_code) 리스트.
            지정하면 88분기 차집합 우회. 누락 검사도 이 리스트로만 한정.
            None이면 기존 _buildAllPeriods 88분기 전체 + 차집합 (heavy fallback).
    """
    from dartlab.providers.dart.openapi.saver import enrichFinance, save

    path = _dataPath("finance", stockCode)

    if targetPeriods is not None:
        # list.json 기반 가벼운 경로: 정확한 (year, code)만 시도.
        # 그 중에서도 이미 로컬에 있는 건 skip.
        if incremental:
            existing = _existingFinancePeriods(path)
            periods = [(y, c) for y, c in targetPeriods if (y, c) not in existing]
        else:
            periods = list(targetPeriods)
    else:
        # 기존 fallback: 88분기 전체 차집합 (heavy)
        allPeriods = _buildAllPeriods()
        if incremental:
            existing = _existingFinancePeriods(path)
            periods = [(y, c) for y, c in allPeriods if (y, c) not in existing]
        else:
            periods = allPeriods

    if not periods:
        return 0

    frames: list[pl.DataFrame] = []
    totalPeriods = len(periods)
    for pIdx, (bsnsYear, reprtCode) in enumerate(periods):
        if client.exhausted:
            break
        quarter = _CODE_TO_QUARTER.get(reprtCode, "Q4")
        if onPeriod:
            onPeriod(f"finance {pIdx + 1}/{totalPeriods} {bsnsYear}{quarter}")
        # CFS (연결) + OFS (별도) 양쪽 수집
        for fsDiv in ("CFS", "OFS"):
            if client.exhausted:
                break
            df = await client.getDf(
                "fnlttSinglAcntAll.json",
                {
                    "corp_code": corpCode,
                    "bsns_year": bsnsYear,
                    "reprt_code": reprtCode,
                    "fs_div": fsDiv,
                },
            )
            if df is None:
                break
            if df.height > 0:
                # API 응답에 fs_div가 없으므로 요청한 값을 직접 부여
                if "fs_div" not in df.columns:
                    df = df.with_columns(pl.lit(fsDiv).alias("fs_div"))
                frames.append(df)

    if not frames:
        return 0

    combined = pl.concat(frames, how="diagonal_relaxed")
    enriched = enrichFinance(combined, stockCode, corpName)
    save(enriched, path)
    return enriched.height


async def _collectReport(
    stockCode: str,
    corpCode: str,
    corpName: str,
    client: AsyncDartClient,
    *,
    incremental: bool = True,
    onPeriod=None,
    targetPeriods: list[tuple[str, str]] | None = None,
) -> int:
    """report 수집. 반환: 저장된 행 수.

    Args:
        targetPeriods: list.json에서 발견한 정확한 (bsns_year, reprt_code).
            지정하면 88분기 차집합 우회.
    """
    from dartlab.providers.dart.openapi.saver import enrichReport, save

    path = _dataPath("report", stockCode)
    allPeriods = list(targetPeriods) if targetPeriods is not None else _buildAllPeriods()

    if incremental:
        existing = _existingReportPeriods(path)
    else:
        existing = set()

    frames: list[pl.DataFrame] = []
    totalCats = len(_PERIODIC_REPORT_CATEGORIES)
    for catIdx, cat in enumerate(_PERIODIC_REPORT_CATEGORIES):
        endpoint = _REPORT_ENDPOINTS.get(cat)
        if not endpoint:
            continue
        if onPeriod:
            onPeriod(f"report {catIdx + 1}/{totalCats} {cat}")
        for bsnsYear, reprtCode in allPeriods:
            if client.exhausted:
                break
            quarterKr = _CODE_TO_QUARTER_KR.get(reprtCode, "4분기")
            engApiType = _KR_TO_ENG_API_TYPE.get(cat, cat)
            # 증분: parquet 실제 포맷(year, "N분기", engApiType)으로 비교
            if incremental and (bsnsYear, quarterKr, engApiType) in existing:
                continue

            df = await client.getDf(
                f"{endpoint}.json",
                {"corp_code": corpCode, "bsns_year": bsnsYear, "reprt_code": reprtCode},
            )
            if df is None:
                break
            if df.height > 0:
                enriched = enrichReport(df, stockCode, corpCode, cat, endpoint)
                frames.append(enriched)
        if client.exhausted:
            break

    if not frames:
        return 0

    combined = pl.concat(frames, how="diagonal_relaxed")
    save(combined, path)
    return combined.height


_processPool = None


def _getProcessPool():
    """XML 파싱용 프로세스 풀 (모듈 레벨 싱글톤)."""
    global _processPool
    if _processPool is None:
        import concurrent.futures
        import os

        _processPool = concurrent.futures.ProcessPoolExecutor(
            max_workers=min(4, (os.cpu_count() or 4)),
        )
    return _processPool


async def _collectDocs(
    stockCode: str,
    corpCode: str,
    corpName: str,
    client: AsyncDartClient,
    *,
    onPeriod=None,
) -> int:
    """docs 수집 (완전 비동기 ZIP 기반)."""
    from dartlab.providers.dart.openapi.zipCollector import (
        _docsDataDir,
        _parseSections,
    )

    if onPeriod:
        onPeriod("docs 목록 조회 중...")

    # 1. 공시 목록 조회 (비동기 페이지네이션)
    allRows: list[dict] = []
    page = 1
    while True:
        if client.exhausted:
            break
        data = await client.getJson(
            "list.json",
            {
                "corp_code": corpCode,
                "bgn_de": "20160101",
                "pblntf_ty": "A",
                "page_count": "100",
                "page_no": str(page),
                "sort": "date",
                "sort_mth": "desc",
            },
            emptyOn013=True,
        )
        if data is None:
            break
        rows = data.get("list", [])
        if not rows:
            break
        allRows.extend(rows)
        totalPage = int(data.get("total_page", 1))
        if page >= totalPage:
            break
        page += 1

    if not allRows:
        return 0

    filings = pl.DataFrame(allRows)
    reportFilter = r"사업보고서|반기보고서|분기보고서"
    filings = filings.filter(pl.col("report_nm").str.contains(reportFilter))
    filings = filings.sort("rcept_dt", descending=True)

    # 기존 수집된 것 제외
    dataDir = _docsDataDir()
    parquetPath = dataDir / f"{stockCode}.parquet"
    existingReports: set[str] = set()
    if parquetPath.exists():
        try:
            df = pl.scan_parquet(parquetPath).select("rcept_no").collect(engine="streaming")
            existingReports = set(df["rcept_no"].unique().to_list())
        except (pl.exceptions.ComputeError, OSError):
            pass

    newFilings = filings.filter(~pl.col("rcept_no").is_in(list(existingReports)))
    if newFilings.height == 0:
        return 0

    # 2. ZIP 수집 (비동기 파이프라인: 다운로드 + 파싱 동시)
    total = newFilings.height
    allSections: list[dict] = []
    failCount = 0
    doneCount = [0]

    async def _fetchOne(rowIdx: int, row: dict) -> None:
        nonlocal failCount
        if client.exhausted:
            return
        rceptNo = row["rcept_no"]
        rceptDt = row["rcept_dt"]
        reportNm = row["report_nm"]

        ym = re.search(r"\((\d{4})\.\d{2}\)", reportNm)
        year = ym.group(1) if ym else rceptDt[:4]

        try:
            raw = await client.getBytes("document.xml", {"rcept_no": rceptNo})
        except (httpx.HTTPError, OSError):
            failCount += 1
            doneCount[0] += 1
            if onPeriod:
                onPeriod(f"docs {doneCount[0]}/{total}")
            return

        if raw is None:
            failCount += 1
            doneCount[0] += 1
            if onPeriod:
                onPeriod(f"docs {doneCount[0]}/{total}")
            return

        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            failCount += 1
            doneCount[0] += 1
            if onPeriod:
                onPeriod(f"docs {doneCount[0]}/{total}")
            return

        names = zf.namelist()
        if not names:
            failCount += 1
            doneCount[0] += 1
            if onPeriod:
                onPeriod(f"docs {doneCount[0]}/{total}")
            return

        largest = max(names, key=lambda n: zf.getinfo(n).file_size)
        content = zf.read(largest)

        xmlContent = None
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                xmlContent = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if xmlContent is None:
            xmlContent = content.decode("utf-8", errors="replace")

        loop = asyncio.get_event_loop()
        sections = await loop.run_in_executor(_getProcessPool(), _parseSections, xmlContent)

        for s in sections:
            allSections.append(
                {
                    "corp_code": corpCode,
                    "corp_name": corpName,
                    "stock_code": stockCode,
                    "year": year,
                    "rcept_date": rceptDt,
                    "rcept_no": rceptNo,
                    "report_type": reportNm,
                    "section_order": s["order"],
                    "section_title": s["title"],
                    "section_url": "",
                    "section_content": s["content"],
                }
            )

        doneCount[0] += 1
        if onPeriod:
            onPeriod(f"docs {doneCount[0]}/{total} {reportNm}")

    # 세마포어로 동시 4개씩 다운로드+파싱
    sem = asyncio.Semaphore(4)

    async def _guarded(rowIdx: int, row: dict) -> None:
        async with sem:
            await _fetchOne(rowIdx, row)

    filingRows = list(enumerate(newFilings.iter_rows(named=True)))
    await asyncio.gather(*[_guarded(idx, row) for idx, row in filingRows])

    if not allSections:
        return 0

    # 3. parquet 저장
    newDf = pl.DataFrame(allSections)
    if parquetPath.exists():
        existingDf = pl.read_parquet(parquetPath)
        combinedDf = pl.concat([existingDf, newDf], how="diagonal_relaxed")
    else:
        combinedDf = newDf

    tmpPath = parquetPath.with_suffix(".parquet.tmp")
    combinedDf.write_parquet(tmpPath)
    if parquetPath.exists():
        parquetPath.unlink()
    tmpPath.rename(parquetPath)

    return len(allSections)


# ── async 실행 헬퍼 ──


def _runAsync(coro):
    """이벤트 루프 유무에 따라 코루틴 실행. Marimo/Jupyter 호환."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 루프 없음 — 일반 Python (KeyboardInterrupt는 호출자가 처리)
        return asyncio.run(coro)
    # 이미 루프가 돌고 있음 (Marimo/Jupyter) → 별도 스레드에서 실행
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


# ── 워커 + 배치 ──


def _resolveCorpCode(stockCode: str) -> tuple[str, str]:
    """종목코드 → (corpCode, corpName)."""
    from dartlab.providers.dart.openapi.client import DartClient
    from dartlab.providers.dart.openapi.corpCode import findCorpCode, loadCorpCodes

    client = DartClient()
    codes = loadCorpCodes(client)
    match = codes.filter(pl.col("stock_code") == stockCode)
    if match.height > 0:
        return match["corp_code"][0], match["corp_name"][0]
    code = findCorpCode(client, stockCode)
    return (code or "", stockCode)


async def _workerLoop(
    workerIndex: int,
    client: AsyncDartClient,
    queue: asyncio.Queue,
    categories: list[str],
    results: dict,
    corpMap: dict[str, tuple[str, str]],
    incremental: bool,
    onComplete,
    onStatus,
    onPeriod,
    failures: dict[str, dict[str, str]] | None = None,
    targetPeriodsByCode: dict[str, list[tuple[str, str]]] | None = None,
) -> None:
    """워커: 큐에서 종목 꺼내서 수집. 키 소진 시 종료.

    failures: {stockCode: {category: errorRepr}} 형태로 실패 추적.
    """
    import logging

    logger = logging.getLogger("dartlab.collector")
    while not client.exhausted:
        try:
            stockCode = queue.get_nowait()
        except asyncio.QueueEmpty:
            if onPeriod:
                onPeriod(workerIndex, "", "완료")
            return

        corpCode, corpName = corpMap.get(stockCode, ("", stockCode))
        result: dict[str, int] = {}

        if onStatus:
            onStatus(workerIndex, stockCode, corpName)

        def _periodCb(msg):
            if onPeriod:
                onPeriod(workerIndex, corpName, msg)

        # 이 종목의 list.json 기반 정확한 (year, reprt_code) — 있으면 88분기 우회
        targetPeriods = None
        if targetPeriodsByCode is not None:
            targetPeriods = targetPeriodsByCode.get(stockCode)

        for cat in categories:
            if client.exhausted:
                await queue.put(stockCode)
                return
            try:
                if cat == "finance":
                    count = await _collectFinance(
                        stockCode,
                        corpCode,
                        corpName,
                        client,
                        incremental=incremental,
                        onPeriod=_periodCb,
                        targetPeriods=targetPeriods,
                    )
                elif cat == "report":
                    count = await _collectReport(
                        stockCode,
                        corpCode,
                        corpName,
                        client,
                        incremental=incremental,
                        onPeriod=_periodCb,
                        targetPeriods=targetPeriods,
                    )
                elif cat == "docs":
                    count = await _collectDocs(
                        stockCode,
                        corpCode,
                        corpName,
                        client,
                        onPeriod=_periodCb,
                    )
                else:
                    count = 0
                result[cat] = count
            except asyncio.CancelledError:
                return
            except (
                httpx.HTTPError,
                OSError,
                ValueError,
                KeyError,
                RuntimeError,
                zipfile.BadZipFile,
            ) as e:
                result[cat] = 0
                # P0 수정 (2026-04-06): 무성한 try/except → 로깅 + 실패 사전 기록.
                # 과거에는 388개 종목 누락 원인이 추적 불가였음.
                errMsg = f"{type(e).__name__}: {e!s}"[:200]
                logger.warning(
                    "collect.fail stockCode=%s category=%s err=%s",
                    stockCode,
                    cat,
                    errMsg,
                )
                if failures is not None:
                    failures.setdefault(stockCode, {})[cat] = errMsg

        if not client.exhausted:
            results[stockCode] = result
            if onComplete:
                catSummary = " ".join(f"{k}:{v}" for k, v in result.items() if v > 0)
                onComplete(corpName, catSummary)

        queue.task_done()


def _resolveCorpMap(stockCodes: list[str]) -> dict[str, tuple[str, str]]:
    """종목코드 목록 → {stockCode: (corpCode, corpName)} 맵."""
    from dartlab.providers.dart.openapi.client import DartClient
    from dartlab.providers.dart.openapi.corpCode import loadCorpCodes

    client = DartClient()
    codes = loadCorpCodes(client)
    corpMap: dict[str, tuple[str, str]] = {}
    for sc in stockCodes:
        match = codes.filter(pl.col("stock_code") == sc)
        if match.height > 0:
            corpMap[sc] = (match["corp_code"][0], match["corp_name"][0])
        else:
            corpMap[sc] = ("", sc)
    return corpMap


def batchCollect(
    stockCodes: list[str],
    *,
    categories: list[str] | None = None,
    maxWorkers: int | None = None,
    incremental: bool = True,
    showProgress: bool = True,
    targetPeriodsByCode: dict[str, list[tuple[str, str]]] | None = None,
) -> dict[str, dict[str, int]]:
    """병렬 배치 수집. 키 N개 → 워커 N개 → 종목 분배.

    Returns: {"005930": {"finance": 120, "report": 450, "docs": 1681}, ...}

    Args:
        targetPeriodsByCode: list.json에서 발견한 종목별 정확한 (year, reprt_code).
            지정하면 _collectFinance/_collectReport가 88분기 차집합 우회.

    Raises:
        없음.

    Example:
        >>> batchCollect(...)

    SeeAlso:
        - ``batchCollect`` / ``batchCollectAll`` — batch 진입.

    Requires:
        - asyncio
        - dartlab
        - datetime
        - httpx
        - io

    Capabilities:
        - DART OpenAPI 배치 수집 단계 — asyncio 기반 N-키 분배.

    Guide:
        - 운영자 batch 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal batch helper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 batch → 일 한도 초과. 키 N 개 필수.
            - 동시 워커 수 >> 키 수 → rate limit.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEYS.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 list → asyncio Queue → DART API → parquet.
        TargetMarkets:
            - KR (DART) 배치 수집.
    """
    cats = categories or ["finance", "report", "docs"]
    keys = resolveDartKeys()
    if not keys:
        raise ValueError("DART API 키가 필요합니다. DART_API_KEYS 환경변수를 설정하세요.")

    if maxWorkers is not None:
        keys = keys[:maxWorkers]

    # corpCode 맵 사전 로드
    corpMap = _resolveCorpMap(stockCodes)
    total = len(stockCodes)

    async def _run(completeFn, statusFn, periodFn) -> dict[str, dict[str, int]]:
        clients = [AsyncDartClient(k) for k in keys]
        queue: asyncio.Queue = asyncio.Queue()
        for sc in stockCodes:
            await queue.put(sc)

        results: dict[str, dict[str, int]] = {}
        failures: dict[str, dict[str, str]] = {}

        try:
            workers = [
                asyncio.create_task(
                    _workerLoop(
                        i,
                        c,
                        queue,
                        cats,
                        results,
                        corpMap,
                        incremental,
                        completeFn,
                        statusFn,
                        periodFn,
                        failures,
                        targetPeriodsByCode,
                    )
                )
                for i, c in enumerate(clients)
            ]
            await asyncio.gather(*workers)
        finally:
            for c in clients:
                await c.close()

        # P0 수정 (2026-04-06):
        # 1) 큐에 남은 종목 = exhausted로 잘린 종목 → pending 파일 저장
        # 2) 실패한 종목 = 에러 발생 종목 → failures 파일 저장
        # 다음 실행에서 이 두 파일을 읽고 우선 재시도해야 누락 회복 가능.
        from dartlab.core.messaging import emit

        pending: list[str] = []
        while not queue.empty():
            try:
                pending.append(queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if pending or failures:
            import os

            from dartlab import config as _cfg

            # 병렬 Job (sync-finance-report / sync-docs) 간 동시 쓰기 경쟁 회피 —
            # env SYNC_STATE_SCOPE 로 하위 디렉토리 분리 (fr / docs).
            baseDir = Path(_cfg.dataDir) / "dart" / "_collect_state"
            scope = os.environ.get("SYNC_STATE_SCOPE", "").strip()
            stateDir = baseDir / scope if scope else baseDir
            stateDir.mkdir(parents=True, exist_ok=True)
            if pending:
                (stateDir / "pending.txt").write_text("\n".join(pending), encoding="utf-8")
                emit("collect:exhausted")
            if failures:
                import json

                (stateDir / "failures.json").write_text(
                    json.dumps(failures, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

        return results

    if not showProgress:
        try:
            return _runAsync(_run(None, None, None))
        except KeyboardInterrupt:
            _log.info("\n[배치] 사용자 중단.")
            return {}

    # ── progress 모드: rich Live 기반 워커별 실시간 표시 ──
    import threading

    from rich.live import Live
    from rich.table import Table
    from rich.text import Text

    numWorkers = len(keys)
    workerLines = ["⏳ 대기 중..."] * numWorkers
    completedCount = [0]
    lock = threading.Lock()
    result: dict[str, dict[str, int]] = {}
    runError: list[BaseException] = []

    ", ".join(cats)

    def _buildDisplay() -> Table:
        """워커 상태 + 전체 진행 bar를 rich Table로 구성."""
        tbl = Table.grid(padding=(0, 1))
        tbl.add_column(style="bold cyan", width=4)
        tbl.add_column()

        for i in range(numWorkers):
            tbl.add_row(f"W{i}", workerLines[i])

        # progress bar
        pct = completedCount[0] / total * 100 if total else 0
        filled = int(pct / 2)
        barStr = "█" * filled + "░" * (50 - filled)
        barText = Text(f"[{barStr}] {completedCount[0]}/{total} ({pct:.0f}%)")
        tbl.add_row("", barText)
        return tbl

    def completeFn(corpName: str, catSummary: str) -> None:
        """completeFn — TODO 한국어 동작 설명.

        Args:
            corpName: 인자.
            catSummary: 인자.

        Raises:
            없음.

        Example:
            >>> completeFn(...)

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        with lock:
            completedCount[0] += 1
            for wIdx in range(numWorkers):
                if corpName in workerLines[wIdx] and "✓" not in workerLines[wIdx]:
                    summary = f" ({catSummary})" if catSummary else ""
                    workerLines[wIdx] = f"✓ {corpName}{summary}"
                    break

    def statusFn(workerIdx: int, stockCode: str, corpName: str) -> None:
        """statusFn — TODO 한국어 동작 설명.

        Args:
            workerIdx: 인자.
            stockCode: 인자.
            corpName: 인자.

        Raises:
            없음.

        Example:
            >>> statusFn(...)

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        with lock:
            workerLines[workerIdx] = f"{corpName} ({stockCode})"

    def periodFn(workerIdx: int, corpName: str, detail: str) -> None:
        """periodFn — TODO 한국어 동작 설명.

        Args:
            workerIdx: 인자.
            corpName: 인자.
            detail: 인자.

        Raises:
            없음.

        Example:
            >>> periodFn(...)

        SeeAlso:
            - ``batchCollect`` / ``batchCollectAll`` — batch 진입.
            - ``resolveDartKeys`` — 멀티 키 resolve.

        Requires:
            - asyncio
            - dartlab
            - datetime
            - httpx
            - io

        Capabilities:
            - DART OpenAPI 배치 수집 단계 (단일 호출 / 워커 / 결과 수집). asyncio 기반 N-키 분배.

        Guide:
            - 운영자 batch 수집 파이프라인 — 사용자 API 가 직접 호출 X.

        AIContext:
            internal batch helper — AI 직접 호출 X.

        LLM Specifications:
            AntiPatterns:
                - 단일 키로 대량 batch (1만+ 종목) → 일 한도 초과. 키 N 개 (DART_API_KEYS) 필수.
                - 동시 워커 수 >> 키 수 → rate limit. 워커 = 키 수.
            OutputSchema:
                - dict / pl.DataFrame / Path — 함수별.
            Prerequisites:
                - 인터넷 + DART_API_KEY (또는 DART_API_KEYS).
            Freshness:
                - DART OpenAPI 실시간.
            Dataflow:
                - 종목 list → asyncio Queue → 워커 N → DART API → parquet 저장.
            TargetMarkets:
                - KR (DART) 배치 수집.
        """
        with lock:
            workerLines[workerIdx] = f"{corpName} | {detail}"

    def _threadTarget():
        try:
            nonlocal result
            result = asyncio.run(_run(completeFn, statusFn, periodFn))
        except KeyboardInterrupt:
            pass
        except BaseException as exc:
            runError.append(exc)

    t = threading.Thread(target=_threadTarget, daemon=True)
    t.start()

    try:
        with Live(_buildDisplay(), refresh_per_second=8) as live:
            while t.is_alive():
                with lock:
                    live.update(_buildDisplay())
                t.join(timeout=0.12)
            # 최종 갱신
            with lock:
                live.update(_buildDisplay())
    except KeyboardInterrupt:
        _log.info("\n[배치] 사용자 중단.")

    if runError and not isinstance(runError[0], KeyboardInterrupt):
        raise runError[0]

    return result


def batchCollectAll(
    *,
    categories: list[str] | None = None,
    mode: str = "new",
    maxWorkers: int | None = None,
    incremental: bool = True,
    showProgress: bool = True,
) -> dict[str, dict[str, int]]:
    """전체 상장종목 배치 수집.

    mode:
      "new" — 파일 없는 종목만
      "all" — 전체

    Args:
        categories: 인자.
        mode: 인자.
        maxWorkers: 인자.
        incremental: 인자.
        showProgress: 인자.

    Raises:
        없음.

    Example:
        >>> batchCollectAll(...)

    Returns:
        dict[str, dict[str, int]] — 종목 × 카테고리 별 수집 통계.

    SeeAlso:
        - ``batchCollect`` / ``batchCollectAll`` — batch 진입.

    Requires:
        - asyncio
        - dartlab
        - datetime
        - httpx
        - io

    Capabilities:
        - DART OpenAPI 배치 수집 단계 — asyncio 기반 N-키 분배.

    Guide:
        - 운영자 batch 수집 파이프라인 — 사용자 API 직접 호출 X.

    AIContext:
        internal batch helper — AI 직접 호출 X.

    LLM Specifications:
        AntiPatterns:
            - 단일 키로 대량 batch → 일 한도 초과. 키 N 개 필수.
            - 동시 워커 수 >> 키 수 → rate limit.
        OutputSchema:
            - dict / pl.DataFrame / Path — 함수별.
        Prerequisites:
            - 인터넷 + DART_API_KEYS.
        Freshness:
            - DART OpenAPI 실시간.
        Dataflow:
            - 종목 list → asyncio Queue → DART API → parquet.
        TargetMarkets:
            - KR (DART) 배치 수집.
    """
    from dartlab.core.listingResolver import getListingResolver

    resolver = getListingResolver()
    if resolver is None:
        return {}
    kindDf = resolver.kindList()
    # 코넥스 제외 (공시 제한적, 사용자 관심 대상 아님)
    kindDf = kindDf.filter(pl.col("시장구분") != "코넥스")
    allCodes = kindDf["종목코드"].to_list()

    if mode == "new":
        cats = categories or ["finance", "report", "docs"]
        newCodes = []
        for sc in allCodes:
            missing = any(not _dataPath(cat, sc).exists() for cat in cats)
            if missing:
                newCodes.append(sc)
        targetCodes = newCodes
    else:
        targetCodes = allCodes

    if not targetCodes:
        _log.info("[배치] 수집할 종목이 없습니다.")
        return {}

    _log.info(f"[배치] {mode} 모드: {len(targetCodes)}개 종목")
    return batchCollect(
        targetCodes,
        categories=categories,
        maxWorkers=maxWorkers,
        incremental=incremental,
        showProgress=showProgress,
    )
