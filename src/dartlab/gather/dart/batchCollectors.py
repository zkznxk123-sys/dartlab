"""dart/openapi batch 단일 종목 비동기 수집기 — batch.py 분할 (규칙 3 LoC).

_collectFinance / _collectReport / _collectDocs + ProcessPool 헬퍼.
"""

from __future__ import annotations

import asyncio
import io
import re
import zipfile
from typing import TYPE_CHECKING

import httpx
import polars as pl

# batch ↔ batchCollectors 양방향 import 회피 — AsyncDartClient 는 type annotation
# (`from __future__ import annotations` 효과로 string lazy), 10 상수/helper 는 함수 본문
# 안만 사용 → 각 함수 시작 lazy import.
if TYPE_CHECKING:
    from dartlab.gather.dart.batch import AsyncDartClient

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
    from dartlab.core.dartBuild import enrichFinance, save, saveReplacingByKeys
    from dartlab.gather.dart.batch import (
        _CODE_TO_QUARTER,
        _buildAllPeriods,
        _dataPath,
        _existingFinancePeriods,
    )

    path = _dataPath("finance", stockCode)

    if targetPeriods is not None:
        # list.json 기반 경로: 발견된 (year, code)는 기존 period가 있어도 다시 수집한다.
        # 정정 공시는 rcept_no가 새롭지만 period는 동일하므로 period 존재 여부로 skip하면 안 된다.
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
    if targetPeriods is not None:
        keyColumns = ["bsns_year", "reprt_code"]
        if "fs_div" in enriched.columns:
            keyColumns.append("fs_div")
        saveReplacingByKeys(enriched, path, keyColumns)
    else:
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
    from dartlab.core.dartBuild import enrichReport, save, saveReplacingByKeys
    from dartlab.gather.dart.batch import (
        _CODE_TO_QUARTER_KR,
        _KR_TO_ENG_API_TYPE,
        _PERIODIC_REPORT_CATEGORIES,
        _REPORT_ENDPOINTS,
        _buildAllPeriods,
        _dataPath,
        _existingReportPeriods,
    )

    path = _dataPath("report", stockCode)
    allPeriods = list(targetPeriods) if targetPeriods is not None else _buildAllPeriods()

    if incremental and targetPeriods is None:
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
    if targetPeriods is not None:
        saveReplacingByKeys(combined, path, ["year", "quarter", "apiType"])
    else:
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
    from dartlab.gather.dart.zipCollector import (
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

    # 3. parquet 저장 (Phase A — writeParquetSorted 가 row group sort + statistics 적용)
    from dartlab.core.dartBuild import writeParquetSorted

    newDf = pl.DataFrame(allSections)
    if parquetPath.exists():
        existingDf = pl.read_parquet(parquetPath)
        combinedDf = pl.concat([existingDf, newDf], how="diagonal_relaxed")
    else:
        combinedDf = newDf

    writeParquetSorted(combinedDf, parquetPath)

    return len(allSections)
