"""경량 일일 동기화 — 새 정기보고서가 올라온 종목만 증분 수집.

흐름:
  1. DART list.json으로 최근 N일 정기공시 조회 (API 1회)
  2. 사업보고서/반기보고서/분기보고서 필터링
  3. 기존 docs parquet의 rcept_no와 비교 → 새 보고서가 있는 종목만 추출
  4. 해당 종목만 증분 수집 + 변경 파일 기록

환경변수:
  DART_API_KEYS: DART OpenAPI 키 (쉼표 구분)
  SYNC_LOOKBACK_DAYS: 조회 기간 (기본: 7일)
  SYNC_CATEGORIES: 수집 카테고리 (기본: finance,report,docs)
  DARTLAB_DATA_DIR: 데이터 저장 경로 (기본: ./data)
"""

import asyncio
import hashlib
import io
import os
import re
import sys
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


def _fileHash(path: Path) -> str:
    """파일 SHA-256 해시 (첫 64KB + 파일크기)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(65536))
        h.update(str(path.stat().st_size).encode())
    return h.hexdigest()


def _snapshotHashes(directory: Path, targets: set[str]) -> dict[str, str]:
    """특정 종목코드 파일만 해시 스냅샷."""
    result = {}
    for sc in targets:
        p = directory / f"{sc}.parquet"
        if p.exists():
            result[p.name] = _fileHash(p)
    return result


def _cloneCategory(category: str, dataDir: str, targetCodes: set[str]) -> int:
    """HF에서 대상 종목 parquet만 개별 다운로드."""
    from dartlab.core.dataConfig import DATA_RELEASES, hfBaseUrl

    dirPath = DATA_RELEASES[category]["dir"]
    localDir = Path(dataDir) / dirPath
    localDir.mkdir(parents=True, exist_ok=True)

    baseUrl = hfBaseUrl(category)
    downloaded = 0

    for sc in targetCodes:
        dest = localDir / f"{sc}.parquet"
        if dest.exists():
            continue
        url = f"{baseUrl}/{sc}.parquet"
        try:
            import urllib.request
            urllib.request.urlretrieve(url, str(dest))
            downloaded += 1
        except Exception:
            pass  # HF에 없는 신규 종목은 무시

    existing = len(list(localDir.glob("*.parquet")))
    if downloaded:
        print(f"[syncRecent] {category}: HF에서 {downloaded}개 다운로드, 총 {existing}개")
    return existing


def _existingRceptNos(docsDir: Path, stockCode: str) -> set[str]:
    """기존 docs parquet에서 rcept_no 집합 추출."""
    import polars as pl

    path = docsDir / f"{stockCode}.parquet"
    if not path.exists():
        return set()
    try:
        df = pl.scan_parquet(path).select("rcept_no").collect()
        return set(df["rcept_no"].unique().to_list())
    except (pl.exceptions.ComputeError, OSError):
        return set()


def _existingFinanceReprts(financeDir: Path, stockCode: str) -> set[tuple[str, str]]:
    """기존 finance parquet의 (bsns_year, reprt_code) 세트 — 어느 보고서가 이미 들어와 있는지."""
    import polars as pl

    path = financeDir / f"{stockCode}.parquet"
    if not path.exists():
        return set()
    try:
        df = (
            pl.scan_parquet(path)
            .select("bsns_year", "reprt_code")
            .filter(pl.col("bsns_year").is_not_null() & pl.col("reprt_code").is_not_null())
            .unique()
            .collect()
        )
        return set(
            zip(
                df["bsns_year"].cast(pl.Utf8).to_list(),
                df["reprt_code"].cast(pl.Utf8).to_list(),
            )
        )
    except (pl.exceptions.ComputeError, OSError):
        return set()


def _reportNmToFinanceKey(reportNm: str) -> tuple[str, str] | None:
    """보고서명 → (bsns_year, reprt_code) 매핑.

    예: "사업보고서 (2025.12)" → ("2025", "11011")
    """
    import re

    yearMatch = re.search(r"\((\d{4})\.(\d{2})\)", reportNm)
    if not yearMatch:
        return None
    year = yearMatch.group(1)

    if reportNm.startswith("사업보고서"):
        return (year, "11011")
    if reportNm.startswith("반기보고서"):
        return (year, "11012")
    if reportNm.startswith("분기보고서"):
        # 분기는 (2025.03) → Q1, (2025.09) → Q3
        month = yearMatch.group(2)
        if month == "03":
            return (year, "11013")
        if month == "09":
            return (year, "11014")
    return None


def _discoverNewFilings(
    keys: str, lookbackDays: int, dataDir: str
) -> tuple[set[str], dict[str, list[dict]]]:
    """최근 N일 정기공시에서 새 보고서 있는 종목 + rcept_no 매핑 반환.

    Returns:
        (targetCodes, codeToFilings)
        codeToFilings: {stockCode: [{rcept_no, rcept_dt, report_nm, corp_code, corp_name}, ...]}
    """
    from dartlab.providers.dart.openapi.client import DartApiError, DartClient
    from dartlab.providers.dart.openapi.disclosure import listFilings
    from dartlab.core.dataConfig import DATA_RELEASES

    import polars as pl

    end = datetime.now()
    start = end - timedelta(days=lookbackDays)

    # 키 로테이션: 여러 키가 있으면 순서대로 시도
    keyList = [k.strip() for k in keys.split(",") if k.strip()]
    filings = None

    for apiKey in keyList:
        try:
            client = DartClient(apiKey=apiKey)
            filings = listFilings(
                client,
                corp=None,
                start=start.strftime("%Y%m%d"),
                end=end.strftime("%Y%m%d"),
                filingType="A",
                fetchAll=True,
            )
            break  # 성공
        except DartApiError as e:
            if "020" in str(e):
                print(f"[syncRecent] API 한도 초과 (키 {apiKey[:8]}...), 다음 키 시도")
                continue
            raise

    if filings is None:
        print("[syncRecent] 모든 API 키 한도 초과 → 수집 불가, 다음 실행까지 대기")
        return set(), {}

    if filings.height == 0:
        print("[syncRecent] 최근 정기공시 없음")
        return set(), {}

    reportFilter = r"^(사업보고서|반기보고서|분기보고서|\[기재정정\]|\[첨부정정\]|\[첨부추가\])"
    filtered = filings.filter(
        pl.col("report_nm").str.contains(reportFilter)
        & pl.col("stock_code").is_not_null()
        & (pl.col("stock_code") != "")
        & (pl.col("stock_code") != " ")
    )

    if filtered.height == 0:
        print("[syncRecent] 대상 보고서 없음")
        return set(), {}

    allCandidateCodes = set(filtered["stock_code"].unique().to_list())

    # docs + finance + report parquet 확보 (비교용)
    _cloneCategory("docs", dataDir, allCandidateCodes)
    _cloneCategory("finance", dataDir, allCandidateCodes)
    _cloneCategory("report", dataDir, allCandidateCodes)

    # 종목별 filing 매핑
    codeToFilings: dict[str, list[dict]] = {}
    for row in filtered.iter_rows(named=True):
        sc = row["stock_code"]
        codeToFilings.setdefault(sc, []).append(row)

    # P0 수정 (2026-04-06): 카테고리별 독립 누락 검사.
    # 과거 버그: docs의 rcept_no만 비교 → docs는 이미 새 보고서가 들어와 있으면
    # finance/report가 누락된 상태여도 targetCodes에서 빠져 영구 누락.
    # 수정: docs 새 rcept_no OR finance에 (year, reprt_code)가 누락된 종목 모두 포함.
    docsDir = Path(dataDir) / DATA_RELEASES["docs"]["dir"]
    financeDir = Path(dataDir) / DATA_RELEASES["finance"]["dir"]
    targetCodes: set[str] = set()
    targetFilings: dict[str, list[dict]] = {}
    docsNewCount = 0
    financeMissingCount = 0

    for sc, rows in codeToFilings.items():
        existingDocs = _existingRceptNos(docsDir, sc)
        existingFinance = _existingFinanceReprts(financeDir, sc)

        # 이 종목에서 새로 발견된 docs rcept_no
        newRowsDocs = [r for r in rows if r["rcept_no"] not in existingDocs]

        # 이 종목에서 finance가 누락된 (year, reprt_code) — list.json의 최신 보고서들 기준
        missingFinance = []
        for r in rows:
            key = _reportNmToFinanceKey(r["report_nm"])
            if key is not None and key not in existingFinance:
                missingFinance.append(r)

        if newRowsDocs:
            docsNewCount += 1
        if missingFinance:
            financeMissingCount += 1

        # 둘 중 하나라도 있으면 수집 대상
        if newRowsDocs or missingFinance:
            targetCodes.add(sc)
            # docs 수집용 — newRowsDocs 우선, 없으면 finance 누락 행을 docs 수집용으로 사용
            targetFilings[sc] = newRowsDocs if newRowsDocs else missingFinance

    skipped = len(allCandidateCodes) - len(targetCodes)
    reportNames = filtered["report_nm"].unique().to_list()
    print(f"[syncRecent] 최근 {lookbackDays}일 정기공시: {filtered.height}건, {len(allCandidateCodes)}개 종목")
    print(f"[syncRecent] 보고서 유형: {reportNames}")
    print(
        f"[syncRecent] 수집 대상: {len(targetCodes)}개 "
        f"(docs 새 rcept_no={docsNewCount}, finance 누락={financeMissingCount}, 스킵={skipped})"
    )

    return targetCodes, targetFilings


# ── docs 직접 수집 (listing API 재조회 없이 rcept_no로 직접 ZIP 다운로드) ──


async def _collectDocsDirect(
    targetFilings: dict[str, list[dict]],
    dataDir: str,
    keys: str,
) -> dict[str, int]:
    """이미 발견한 rcept_no들의 ZIP만 직접 다운로드 + 파싱.

    batchCollect._collectDocs와 달리 per-stock listing API를 호출하지 않는다.
    이것이 타임아웃의 근본 원인이었음.
    """
    from dartlab.core.dataConfig import DATA_RELEASES
    from dartlab.providers.dart.openapi.batch import AsyncDartClient
    from dartlab.providers.dart.openapi.zipCollector import _parseSections

    import polars as pl

    docsDir = Path(dataDir) / DATA_RELEASES["docs"]["dir"]
    docsDir.mkdir(parents=True, exist_ok=True)

    keyList = [k.strip() for k in keys.split(",") if k.strip()]
    client = AsyncDartClient(keyList[0])

    # 모든 filing을 flat list로 변환
    allJobs: list[tuple[str, dict]] = []
    for sc, rows in targetFilings.items():
        for row in rows:
            allJobs.append((sc, row))

    total = len(allJobs)
    doneCount = [0]
    failCount = [0]
    stockSections: dict[str, list[dict]] = {}  # stockCode → sections

    sem = asyncio.Semaphore(4)  # 동시 4개 다운로드 (API 한도 소진 속도 조절)

    async def _fetchOne(stockCode: str, row: dict) -> None:
        if client.exhausted:
            return

        rceptNo = row["rcept_no"]
        rceptDt = row.get("rcept_dt", "")
        reportNm = row.get("report_nm", "")
        corpCode = row.get("corp_code", "")
        corpName = row.get("corp_name", stockCode)

        ym = re.search(r"\((\d{4})\.\d{2}\)", reportNm)
        year = ym.group(1) if ym else rceptDt[:4]

        try:
            raw = await client.getBytes("document.xml", {"rcept_no": rceptNo})
        except Exception:
            failCount[0] += 1
            doneCount[0] += 1
            return

        if raw is None:
            failCount[0] += 1
            doneCount[0] += 1
            return

        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            failCount[0] += 1
            doneCount[0] += 1
            return

        names = zf.namelist()
        if not names:
            failCount[0] += 1
            doneCount[0] += 1
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
        sections = await loop.run_in_executor(None, _parseSections, xmlContent)

        if stockCode not in stockSections:
            stockSections[stockCode] = []

        for s in sections:
            stockSections[stockCode].append(
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
        if doneCount[0] % 10 == 0 or doneCount[0] == total:
            print(f"[syncRecent] docs: {doneCount[0]}/{total} 완료 (실패: {failCount[0]})")

    async def _guarded(stockCode: str, row: dict) -> None:
        async with sem:
            try:
                await asyncio.wait_for(_fetchOne(stockCode, row), timeout=120)
            except asyncio.TimeoutError:
                failCount[0] += 1
                doneCount[0] += 1
                print(f"[syncRecent] docs 타임아웃: {stockCode} {row.get('rcept_no', '?')}")

    await asyncio.gather(*[_guarded(sc, row) for sc, row in allJobs])
    await client.close()

    # 종목별 parquet 저장
    results: dict[str, int] = {}
    for sc, sections in stockSections.items():
        if not sections:
            continue

        parquetPath = docsDir / f"{sc}.parquet"
        newDf = pl.DataFrame(sections)

        if parquetPath.exists():
            try:
                existingDf = pl.read_parquet(parquetPath)
                combinedDf = pl.concat([existingDf, newDf], how="diagonal_relaxed")
            except (pl.exceptions.ComputeError, OSError):
                combinedDf = newDf
        else:
            combinedDf = newDf

        tmpPath = parquetPath.with_suffix(".parquet.tmp")
        combinedDf.write_parquet(tmpPath)
        if parquetPath.exists():
            parquetPath.unlink()
        tmpPath.rename(parquetPath)

        results[sc] = len(sections)

    print(f"[syncRecent] docs 직접 수집 완료: {len(results)}개 종목, {sum(results.values())}개 섹션")
    return results


def main():
    keys = os.environ.get("DART_API_KEYS", "")
    if not keys:
        print("DART_API_KEYS 환경변수가 필요합니다.")
        sys.exit(1)

    lookbackDays = int(os.environ.get("SYNC_LOOKBACK_DAYS", "7"))
    categories = [
        c.strip()
        for c in os.environ.get("SYNC_CATEGORIES", "finance,report,docs").split(",")
        if c.strip()
    ]

    if "DARTLAB_DATA_DIR" not in os.environ:
        os.environ["DARTLAB_DATA_DIR"] = os.path.join(os.getcwd(), "data")
    dataDir = os.environ["DARTLAB_DATA_DIR"]
    os.makedirs(dataDir, exist_ok=True)

    print(f"[syncRecent] lookback={lookbackDays}일, categories={categories}, dataDir={dataDir}")

    # 0단계: 이전 실행에서 잘린 종목 (pending.txt) 우선 회수
    pendingPath = Path(dataDir) / "dart" / "_collect_state" / "pending.txt"
    pendingCodes: set[str] = set()
    if pendingPath.exists():
        pendingCodes = set(
            line.strip() for line in pendingPath.read_text(encoding="utf-8").splitlines() if line.strip()
        )
        if pendingCodes:
            print(f"[syncRecent] 이전 실행 pending: {len(pendingCodes)}개 종목 우선 처리")

    # 1단계: 새 보고서가 있는 종목 발견
    targetCodes, targetFilings = _discoverNewFilings(keys, lookbackDays, dataDir)

    # pending과 합침 (우선)
    targetCodes = targetCodes | pendingCodes

    if not targetCodes:
        print("[syncRecent] 수집 대상 없음 → 종료")
        distDir = Path("dist")
        distDir.mkdir(exist_ok=True)
        for cat in categories:
            (distDir / f"changed_{cat}.txt").write_text("", encoding="utf-8")
        (distDir / "changed.txt").write_text("", encoding="utf-8")
        return

    # 2단계: 기존 데이터 확보 (HF에서 다운로드)
    from dartlab.core.dataConfig import DATA_RELEASES

    for cat in categories:
        if cat != "docs":  # docs는 _discoverNewFilings에서 이미 확보
            _cloneCategory(cat, dataDir, targetCodes)

    # 3단계: 수집 전 해시 스냅샷
    allBeforeHashes: dict[str, dict[str, str]] = {}
    for cat in categories:
        localDir = Path(dataDir) / DATA_RELEASES[cat]["dir"]
        allBeforeHashes[cat] = _snapshotHashes(localDir, targetCodes)

    # 4단계: 카테고리별 수집
    startTime = time.time()

    if "docs" in categories and len(categories) == 1:
        # docs 전용 모드: 직접 ZIP 수집 (listing API 재조회 없음)
        asyncio.run(_collectDocsDirect(targetFilings, dataDir, keys))
    elif "docs" not in categories:
        # finance/report만: batchCollect 사용 (88분기 차집합 우회)
        from dartlab.providers.dart.openapi.batch import batchCollect

        # list.json 발견 결과에서 종목별 정확한 (year, reprt_code) 추출
        targetPeriodsByCode: dict[str, list[tuple[str, str]]] = {}
        for sc, rows in targetFilings.items():
            keys_set = set()
            for r in rows:
                k = _reportNmToFinanceKey(r["report_nm"])
                if k is not None:
                    keys_set.add(k)
            if keys_set:
                targetPeriodsByCode[sc] = sorted(keys_set)

        batchCollect(
            list(targetCodes),
            categories=categories,
            incremental=True,
            showProgress=False,
            targetPeriodsByCode=targetPeriodsByCode,
        )
    else:
        # 혼합 모드 (fallback): batchCollect로 전체 수집
        from dartlab.providers.dart.openapi.batch import batchCollect

        # finance/report 카테고리에 대해 list.json 기반 정확한 (year, reprt_code) 추출
        targetPeriodsByCode = {}
        for sc, rows in targetFilings.items():
            keys_set = set()
            for r in rows:
                k = _reportNmToFinanceKey(r["report_nm"])
                if k is not None:
                    keys_set.add(k)
            if keys_set:
                targetPeriodsByCode[sc] = sorted(keys_set)

        batchCollect(
            list(targetCodes),
            categories=categories,
            incremental=True,
            showProgress=False,
            targetPeriodsByCode=targetPeriodsByCode,
        )

    elapsed = time.time() - startTime

    # pending.txt 비움 — collector가 새로 exhausted되면 batchCollect가 새 pending.txt를 작성
    if pendingPath.exists():
        try:
            pendingPath.unlink()
        except OSError:
            pass

    # 5단계: 변경 파일 감지
    allChanged: dict[str, list[str]] = {}
    allNew: dict[str, list[str]] = {}

    for cat in categories:
        localDir = Path(dataDir) / DATA_RELEASES[cat]["dir"]
        afterHashes = _snapshotHashes(localDir, targetCodes)
        beforeHashes = allBeforeHashes[cat]

        newFiles = [f for f in afterHashes if f not in beforeHashes]
        updatedFiles = [
            f for f in afterHashes
            if f in beforeHashes and afterHashes[f] != beforeHashes[f]
        ]
        allNew[cat] = newFiles
        allChanged[cat] = newFiles + updatedFiles

    # 카테고리별 changed.txt 기록
    distDir = Path("dist")
    distDir.mkdir(exist_ok=True)

    totalChanged = 0
    for cat in categories:
        changedPath = distDir / f"changed_{cat}.txt"
        changedPath.write_text("\n".join(allChanged[cat]), encoding="utf-8")
        totalChanged += len(allChanged[cat])

    # 통합 changed.txt (uploadData.py 호환)
    allChangedFlat = []
    for cat in categories:
        allChangedFlat.extend(allChanged[cat])
    (distDir / "changed.txt").write_text("\n".join(allChangedFlat), encoding="utf-8")

    print(f"[syncRecent] 완료: {len(targetCodes)}개 종목, {elapsed:.0f}초")
    for cat in categories:
        print(f"[syncRecent] {cat}: 신규 {len(allNew[cat])}개 + 업데이트 {len(allChanged[cat]) - len(allNew[cat])}개")

    # GitHub Actions summary
    summaryPath = os.environ.get("GITHUB_STEP_SUMMARY")
    if summaryPath:
        with open(summaryPath, "a", encoding="utf-8") as f:
            f.write(f"## Daily Sync (최근 {lookbackDays}일 공시)\n\n")
            f.write(f"| 항목 | 값 |\n|------|----|\n")
            f.write(f"| 카테고리 | {', '.join(categories)} |\n")
            f.write(f"| 수집 대상 | {len(targetCodes)}개 |\n")
            f.write(f"| 소요 시간 | {elapsed:.0f}초 |\n")
            for cat in categories:
                changed = len(allChanged[cat])
                f.write(f"| {cat} 변경 | {changed}개 |\n")
            f.write(f"| 총 변경 파일 | {totalChanged}개 |\n")


if __name__ == "__main__":
    main()
