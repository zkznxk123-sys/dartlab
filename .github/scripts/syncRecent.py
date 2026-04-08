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


def _loadDocsSkipped(dataDir: str) -> set[str]:
    """document.xml status 014 (파일 없음) 받은 rcept_no 영구 스킵 리스트.

    DART 시스템에 document.xml이 존재하지 않는 보고서가 있다 (정정류 외에도
    원본 보고서 일부). 매 run마다 시도하면 키 낭비 → 한 번 014 받으면 영구 스킵.
    """
    p = Path(dataDir) / "dart" / "_collect_state" / "skipped_docs_rcept.txt"
    if not p.exists():
        return set()
    return {line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()}


def _appendDocsSkipped(dataDir: str, rcepts: set[str]) -> None:
    if not rcepts:
        return
    p = Path(dataDir) / "dart" / "_collect_state" / "skipped_docs_rcept.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = _loadDocsSkipped(dataDir)
    merged = existing | rcepts
    p.write_text("\n".join(sorted(merged)), encoding="utf-8")
    print(f"[syncRecent] docs 영구 스킵 리스트 갱신: +{len(rcepts)}, 총 {len(merged)}")


def _existingRceptNos(directory: Path, stockCode: str) -> set[str]:
    """parquet 파일에서 rcept_no 집합 추출 (docs/finance/report 공통).

    3개 카테고리 모두 `rcept_no` 컬럼을 가지므로 단일 함수로 통일.
    파일이 없거나 컬럼이 없거나 손상된 경우 빈 set.
    """
    import polars as pl

    path = directory / f"{stockCode}.parquet"
    if not path.exists():
        return set()
    try:
        cols = pl.scan_parquet(path).collect_schema().names()
        if "rcept_no" not in cols:
            return set()
        df = (
            pl.scan_parquet(path)
            .select("rcept_no")
            .filter(pl.col("rcept_no").is_not_null() & (pl.col("rcept_no") != ""))
            .unique()
            .collect()
        )
        return set(df["rcept_no"].to_list())
    except (pl.exceptions.ComputeError, pl.exceptions.ColumnNotFoundError, OSError):
        return set()


# report도 docs/finance와 동일 — rcept_no 존재 여부만 본다.
# (이전엔 apiType≥5 partial 임계를 두었으나, 정상 종목까지 재수집 대상으로
#  분류하는 부작용이 있어 폐기. partial은 batchCollect 단계에서 처리한다.)


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

    # 근본 원칙 (2026-04-08): rcept_no를 단일 키로 카테고리별 독립 누락 검사.
    #
    # 정기보고서 list.json의 각 행 = (stockCode, rcept_no) 단위.
    # 이 rcept_no가 docs/finance/report 각 parquet에 들어있는지 독립 검사.
    # - docs: rcept_no 컬럼 직접 비교
    # - finance: rcept_no 컬럼 직접 비교 (정정 보고서도 감지)
    # - report: rcept_no 컬럼 직접 비교 (apiType 임계 폐기 — 정상 종목 오탐 부작용)
    #
    # 종목 단위 targetCodes는 합집합이지만, 카테고리별로 정확히 누락된 (rcept_no/period)만
    # 수집하도록 missingByCat에 분리 저장한다.
    docsDir = Path(dataDir) / DATA_RELEASES["docs"]["dir"]
    financeDir = Path(dataDir) / DATA_RELEASES["finance"]["dir"]
    reportDir = Path(dataDir) / DATA_RELEASES["report"]["dir"]

    docsSkipped = _loadDocsSkipped(dataDir)

    targetCodes: set[str] = set()
    targetFilings: dict[str, list[dict]] = {}  # docs 직접수집용 (rcept_no list)
    missingDocsCount = 0
    missingFinanceCount = 0
    missingReportCount = 0

    # docs 직접 수집은 document.xml API를 쓰는데, 정정/첨부정정/첨부추가/연장신고서는
    # 별도 파일이 존재하지 않아 status 014를 받는다 (DART 시스템 한계).
    # 원본 보고서만 docs 누락 대상으로 본다. finance/report는 정정도 포함 — 데이터 수정이
    # 반영되어야 하므로 batchCollect로 다시 받는다.
    DOCS_EXCLUDE_PREFIX = ("[기재정정]", "[첨부정정]", "[첨부추가]")
    DOCS_EXCLUDE_KEYWORD = "사업보고서제출기한연장신고서"

    def _isDocsTarget(reportNm: str) -> bool:
        if reportNm.startswith(DOCS_EXCLUDE_PREFIX):
            return False
        if DOCS_EXCLUDE_KEYWORD in reportNm:
            return False
        return True

    for sc, rows in codeToFilings.items():
        existingDocs = _existingRceptNos(docsDir, sc)
        existingFinance = _existingRceptNos(financeDir, sc)
        existingReport = _existingRceptNos(reportDir, sc)

        # docs는 원본 보고서만 (정정류 제외) + 영구 스킵 리스트 제외
        docsRows = [r for r in rows if _isDocsTarget(r["report_nm"])]
        missingDocs = [
            r for r in docsRows
            if r["rcept_no"] not in existingDocs and r["rcept_no"] not in docsSkipped
        ]
        missingFinance = [r for r in rows if r["rcept_no"] not in existingFinance]
        missingReport = [r for r in rows if r["rcept_no"] not in existingReport]

        if missingDocs:
            missingDocsCount += 1
        if missingFinance:
            missingFinanceCount += 1
        if missingReport:
            missingReportCount += 1

        if missingDocs or missingFinance or missingReport:
            targetCodes.add(sc)
            # docs 직접 ZIP 수집은 missingDocs 행만 처리.
            # finance/report 수집은 batchCollect가 (year, reprt_code) 기반이므로
            # main()에서 missing rows를 합쳐 targetPeriodsByCode를 구성한다.
            targetFilings[sc] = {
                "docs": missingDocs,
                "finance": missingFinance,
                "report": missingReport,
            }

    skipped = len(allCandidateCodes) - len(targetCodes)
    reportNames = filtered["report_nm"].unique().to_list()
    print(f"[syncRecent] 최근 {lookbackDays}일 정기공시: {filtered.height}건, {len(allCandidateCodes)}개 종목")
    print(f"[syncRecent] 보고서 유형: {reportNames}")
    print(
        f"[syncRecent] 수집 대상: {len(targetCodes)}개 "
        f"(docs 누락={missingDocsCount}, finance 누락={missingFinanceCount}, "
        f"report 누락={missingReportCount}, 스킵={skipped})"
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
    # 모든 키로 client 미리 생성 → 첫 키가 exhausted여도 다음 키로 자동 회전.
    # 이전 버그: keyList[0]만 사용 → 첫 키 exhausted 시 docs 수집 0건으로 즉시 종료.
    clients = [AsyncDartClient(k) for k in keyList]
    clientIdx = [0]

    def _activeClient():
        """exhausted 안 된 첫 client 반환. 모두 exhausted면 None."""
        while clientIdx[0] < len(clients) and clients[clientIdx[0]].exhausted:
            clientIdx[0] += 1
        return clients[clientIdx[0]] if clientIdx[0] < len(clients) else None

    # 모든 docs 누락 filing을 flat list로 변환
    allJobs: list[tuple[str, dict]] = []
    for sc, perCat in targetFilings.items():
        for row in perCat.get("docs", []):
            allJobs.append((sc, row))

    total = len(allJobs)
    doneCount = [0]
    failCount = [0]
    stockSections: dict[str, list[dict]] = {}  # stockCode → sections
    skippedRcepts: set[str] = set()  # status 014 → 영구 스킵 후보

    sem = asyncio.Semaphore(4)  # 동시 4개 다운로드 (API 한도 소진 속도 조절)

    async def _fetchOne(stockCode: str, row: dict) -> None:
        client = _activeClient()
        if client is None:
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

        # status 014 (파일 없음) 감지 → 영구 스킵 마킹
        if len(raw) < 500 and raw.startswith(b"<?xml"):
            try:
                body = raw.decode("utf-8", errors="replace")
                if "<status>014</status>" in body:
                    skippedRcepts.add(rceptNo)
                    failCount[0] += 1
                    doneCount[0] += 1
                    return
            except (UnicodeDecodeError, AttributeError):
                pass

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
    for c in clients:
        await c.close()

    # status 014 받은 rcept_no 영구 스킵 리스트에 누적
    if skippedRcepts:
        _appendDocsSkipped(dataDir, skippedRcepts)

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

    # 2개월 기본 — list.json에 있는데 docs/finance/report에 없는 것만 수집한다.
    # 짧으면 정정 보고서 + 늦은 제출을 놓친다. rcept_no 누락 검사가 정확하므로
    # 길어도 비용은 사실상 list.json 페이징뿐.
    lookbackDays = int(os.environ.get("SYNC_LOOKBACK_DAYS", "60"))
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

    # 카테고리별 정확히 누락된 종목 + (year, reprt_code) 만 수집한다.
    # docs는 별도 직접 ZIP 수집 경로, finance/report는 batchCollect.
    def _periodsFor(cat: str) -> tuple[list[str], dict[str, list[tuple[str, str]]]]:
        """cat에서 누락이 있는 종목 + 그 종목의 누락 (year, reprt_code) list."""
        codes: list[str] = []
        periods: dict[str, list[tuple[str, str]]] = {}
        for sc, perCat in targetFilings.items():
            rows = perCat.get(cat, [])
            if not rows:
                continue
            ks: set[tuple[str, str]] = set()
            for r in rows:
                k = _reportNmToFinanceKey(r["report_nm"])
                if k is not None:
                    ks.add(k)
            if ks:
                codes.append(sc)
                periods[sc] = sorted(ks)
        return codes, periods

    if "docs" in categories:
        asyncio.run(_collectDocsDirect(targetFilings, dataDir, keys))

    nonDocsCats = [c for c in categories if c != "docs"]
    if nonDocsCats:
        from dartlab.providers.dart.openapi.batch import batchCollect

        # finance/report 각각 독립적으로 누락 종목만 수집.
        # 한 카테고리만 누락이면 다른 카테고리는 건드리지 않는다.
        for cat in nonDocsCats:
            codes, periods = _periodsFor(cat)
            if not codes:
                print(f"[syncRecent] {cat}: 누락 없음 → 스킵")
                continue
            print(f"[syncRecent] {cat}: {len(codes)}개 종목 수집 시작")
            batchCollect(
                codes,
                categories=[cat],
                incremental=True,
                showProgress=False,
                targetPeriodsByCode=periods,
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
