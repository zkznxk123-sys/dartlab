"""전체 공시 원문 수집기 — 2단계 증분 수집 + raw 본문 생긴 그대로 보존.

Phase 1: 목록 수집 (collectMeta) — 일자별 API 1회, 매우 가볍다.
Phase 2: 원문 수집 (fillContent) — 건당 API 1회, 키 소비 큼. 본문은 zip 안 largest
파일을 *생긴 그대로* (`content_raw` 컬럼) 저장한다. DART 는 공시 종류별로 두 포맷을
섞어 반환한다 — (a) dart4.xsd XML (`<DOCUMENT>` / `<TITLE ATOC ...>` / `<TABLE>`),
(b) xforms HTML (`<html><head><meta charset="euc-kr"><STYLE>.xforms ...</STYLE>`).
모든 태그·attribute 보존. plain text 가 필요한 소비자는 BeautifulSoup ``lxml``
parser 의 `get_text()` 등으로 변환 (lxml 은 XML/HTML 양쪽 안전). sections
`_raw.parquet` 와 동일 비전.

목록을 먼저 전부 모은 뒤, 원문은 키 여유 있을 때 점진적으로 채운다.

사용법::

    from dartlab.gather.dart.allFilingsCollector import (
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
from dartlab.core.dartClient import DartClient
from dartlab.core.dataConfig import DATA_RELEASES
from dartlab.core.logger import getLogger
from dartlab.core.memory import withMemoryBudget
from dartlab.gather.dart.disclosure import listFilings

_log = getLogger(__name__)

# ── 상수 ──

_ALLFILINGS_DIR_KEY = "allFilings"
_META_SUFFIX = "_meta"  # 목록만: 20260327_meta.parquet
# 원문포함: 20260327.parquet


def metaSuffix() -> str:
    """allFilings 메타 parquet 파일 suffix(``_meta``) — providers 소비자가 core.dartClient seam 으로 접근."""
    return _META_SUFFIX


# 정기공시 (사업/분기/반기보고서) 본문은 panel 이 owner — allFilings 본문 수집에서 스킵.
# 89% 가 docs/ 와 중복 (2026-05 검증). 부피 큰 공시 본문 중복 호출 차단.
_PERIODIC_REPORT_PATTERNS: tuple[str, ...] = ("사업보고서", "분기보고서", "반기보고서")

# ── 내부 유틸 ──


def _allFilingsDir() -> Path:
    """allFilings parquet 저장 디렉토리."""
    root = Path(_cfg.dataDir)
    d = root / DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    d.mkdir(parents=True, exist_ok=True)
    return d


def _collectOneRaw(client: DartClient, rceptNo: str) -> tuple[str | None, str]:
    """단일 공시 원문 raw 본문 반환 — 생긴 그대로, 모든 태그·attribute 보존.

    DART 가 반환하는 zip 안 largest 파일은 공시 종류별로 dart4.xsd XML 또는 xforms
    HTML 두 포맷 중 하나. utf-8/euc-kr/cp949 순으로 디코딩만 한다. 후처리 0.

    Returns:
        (content_raw, fetch_status) tuple.
        fetch_status:
            - ``"ok"``: 정상 본문 수집 — content_raw 는 raw XML/HTML.
            - ``"no_body"``: DART 명시 데이터 truth (행정 통지 / 첨부정정 / 접수번호
              오류). 영원히 retry 불가. status 013 (접수번호 오류) 또는 014 (파일
              부재) 응답. content_raw 는 None.
            - ``"error"``: API 장애 (network · 한도 · 시스템 점검 · decode 실패).
              retry 대상. content_raw 는 None.

    DART API 응답 구조:
        정상: ``b'PK\\x03\\x04'`` ZIP magic prefix → zip 내 largest 파일 디코딩.
        본문 부재: 147 bytes XML ``<result><status>014</status><message>파일이
        존재하지 않습니다</message></result>``.
        접수번호 오류: 147 bytes XML ``<status>013</status><message>접수번호 오류
        ...``.
        기타 에러: status 010/011/012 (API key) · 020 (한도) · 800 (점검) · 900
        (불명) → "error".
    """
    try:
        raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
    except (RuntimeError, OSError):
        return (None, "error")

    if raw is None or len(raw) == 0:
        return (None, "error")

    # 정상 응답 — ZIP magic prefix
    if raw[:4] == b"PK\x03\x04":
        try:
            zf = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile:
            return (None, "error")

        names = zf.namelist()
        if not names:
            return (None, "error")

        largest = max(names, key=lambda n: zf.getinfo(n).file_size)
        content = zf.read(largest)

        rawContent: str | None = None
        for enc in ("utf-8", "euc-kr", "cp949"):
            try:
                rawContent = content.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if rawContent is None:
            rawContent = content.decode("utf-8", errors="replace")

        if not rawContent.strip():
            return (None, "error")

        return (rawContent, "ok")

    # status XML 응답 — DART 명시 결과
    text = raw[:300].decode("utf-8", errors="replace")
    if "<status>014" in text or "<status>013" in text:
        return (None, "no_body")
    return (None, "error")


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

    # listFilings 1 호출 (1.5초) — 항상 호출. 당일 추가 공시 / 옛 날짜 정정공시 발견.
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

    # 저장 — 옛 meta 가 있어도 신규 결과로 덮어씀 (listFilings 는 정정 포함 최신 list 반환).
    # 본문 .parquet 는 fillContent 가 별도 diff 로 incremental update.
    tmpPath = metaPath.with_suffix(".parquet.tmp")
    meta.write_parquet(tmpPath)
    tmpPath.replace(metaPath)

    if showProgress:
        _log.info("[%s] 목록 %d건 갱신", period, meta.height)

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


def _rowFromMeta(metaRow: dict, content: str | None, status: str) -> dict:
    """meta row + 본문 수집 결과 → 본문 parquet row dict."""
    return {
        "corp_code": metaRow["corp_code"],
        "corp_name": metaRow["corp_name"],
        "stock_code": metaRow.get("stock_code", ""),
        "corp_cls": metaRow["corp_cls"],
        "rcept_dt": metaRow["rcept_dt"],
        "rcept_no": metaRow["rcept_no"],
        "report_nm": metaRow["report_nm"],
        "flr_nm": metaRow.get("flr_nm", ""),
        "content_raw": content,
        "fetch_status": status,
    }


def fillContent(
    period: str,
    *,
    client: DartClient | None = None,
    showProgress: bool = True,
) -> pl.DataFrame | None:
    """하루치 본문 incremental 수집. **idempotent + diff retry**.

    매번 호출 시:
        1. ``collectMetaDay`` 호출 — listFilings 1 회 (1.5초) 로 최신 공시 목록 갱신.
           당일 추가 공시 / 옛 날짜 정정공시 발견 보장.
        2. 기존 ``.parquet`` 의 rcept_no → fetch_status 맵 빌드.
        3. 처리 대상:
           - 신규 rcept_no (목록엔 있지만 .parquet 에 없는 것) → 본문 수집
           - 기존 ``fetch_status="error"`` → retry
           - 기존 ``fetch_status="ok"`` / ``"no_body"`` → skip (final)
        4. 정기공시 (``_PERIODIC_REPORT_PATTERNS``) 는 row 자체 생략 — docs/ owner.
        5. atomic merge — skip row + 신규/retry row → tmp.parquet → rename.

    본문 0 건 안전장치 — incremental update (기존 .parquet 있음) 의 경우엔 트리거 X.
    *최초 수집* 에서 모든 row error 일 때만 .parquet 갱신 차단 (옛 사고 가드).

    Args:
        period: YYYYMMDD.
        client: DartClient 인스턴스. None 이면 자동 생성.
        showProgress: True 면 progress 로그.

    Returns:
        pl.DataFrame 또는 None — 본문 .parquet 의 최종 내용. 변경 0 시에도 기존
        .parquet 의 DataFrame 반환. listFilings 결과 0 또는 처리 대상 0 시 None.

    Raises:
        없음.

    Example:
        >>> fillContent("20260527")  # doctest: +SKIP
    """
    if client is None:
        client = DartClient()

    outDir = _allFilingsDir()
    metaPath = outDir / f"{period}{_META_SUFFIX}.parquet"
    fullPath = outDir / f"{period}.parquet"

    # Step 1: meta 갱신 — listFilings 항상 호출.
    collectMetaDay(period, client=client, showProgress=showProgress)
    if not metaPath.exists():
        if showProgress:
            _log.info("[%s] 목록 없음 (휴일)", period)
        return None
    meta = pl.read_parquet(metaPath)

    # Step 2: 기존 본문 .parquet 의 rcept_no → fetch_status 맵 (diff 판정용).
    # 본문 row dict 자체는 후속 concat 단계에서 .parquet 그대로 재사용 — 메모리에 안 올림.
    existingStatus: dict[str, str] = {}
    if fullPath.exists():
        statusDf = pl.read_parquet(fullPath, columns=["rcept_no", "fetch_status"])
        for r in statusDf.iter_rows(named=True):
            existingStatus[r["rcept_no"]] = r["fetch_status"]

    # Step 3: 처리 대상 분리.
    skipPeriodic = 0
    skipExisting = 0
    targets: list[dict] = []  # 신규 + retry — 본문 수집 대상 meta row
    for metaRow in meta.iter_rows(named=True):
        rceptNo = metaRow["rcept_no"]
        reportNm = metaRow.get("report_nm", "") or ""

        # 정기공시 — docs/ owner. row 자체 생략.
        if any(p in reportNm for p in _PERIODIC_REPORT_PATTERNS):
            skipPeriodic += 1
            continue

        existing = existingStatus.get(rceptNo)
        if existing is None:
            targets.append(metaRow)  # 신규
        elif existing == "error":
            targets.append(metaRow)  # retry
        else:
            skipExisting += 1  # ok / no_body — final, skip

    if not targets:
        if showProgress:
            _log.info(
                "[%s] 변경 없음: 기존 ok/no_body %d, 정기공시 skip %d, 처리 대상 0",
                period,
                skipExisting,
                skipPeriodic,
            )
        # 기존 .parquet 이 있으면 그대로 반환, 없으면 None
        return pl.read_parquet(fullPath) if fullPath.exists() else None

    if showProgress:
        _log.info(
            "[%s] 처리 시작: 신규/retry %d, 기존 skip %d (ok/no_body), 정기공시 skip %d",
            period,
            len(targets),
            skipExisting,
            skipPeriodic,
        )

    # Step 4: 본문 수집 — 신규 + retry.
    processedRows: dict[str, dict] = {}
    okCount = noBodyCount = errorCount = 0
    for idx, metaRow in enumerate(targets):
        rceptNo = metaRow["rcept_no"]
        content, status = _collectOneRaw(client, rceptNo)
        processedRows[rceptNo] = _rowFromMeta(metaRow, content, status)
        if status == "ok":
            okCount += 1
        elif status == "no_body":
            noBodyCount += 1
        else:
            errorCount += 1
        if showProgress and (idx + 1) % 100 == 0:
            _log.info(
                "  [%d/%d] ok=%d no_body=%d error=%d",
                idx + 1,
                len(targets),
                okCount,
                noBodyCount,
                errorCount,
            )

    # Step 5: 본문 0 건 성공 안전장치 — 최초 수집만 트리거 (incremental update 는
    # 기존 데이터 보존이 0건 가드보다 우선).
    isFirstFill = not fullPath.exists()
    if isFirstFill and okCount == 0 and errorCount > 0:
        _log.warning(
            "[%s] 최초 수집인데 ok 0 / error %d / no_body %d — .parquet 승격 차단, _meta 보존. "
            "원인 확인 후 재시도 필요 (API 키 한도 / 네트워크 / URL 변경).",
            period,
            errorCount,
            noBodyCount,
        )
        return None

    # Step 6: skip 기존 row + 신규/retry row → atomic merge.
    # polars DataFrame schema 추론은 mixed-size 큰 string row 에서 fragile —
    # 신규 row 만 `infer_schema_length=None` 으로 build 후 기존 .parquet (이미
    # parquet schema 박혀있음) 과 concat 한다.
    processedDf = pl.DataFrame(list(processedRows.values()), infer_schema_length=None)
    if fullPath.exists():
        keepDf = pl.read_parquet(fullPath).filter(~pl.col("rcept_no").is_in(list(processedRows.keys())))
        df = pl.concat([keepDf, processedDf], how="diagonal_relaxed")
    else:
        df = processedDf

    tmpPath = fullPath.with_suffix(".parquet.tmp")
    df.write_parquet(tmpPath)
    tmpPath.replace(fullPath)

    # _meta 제거 (.parquet 승격 완료) — 매번 호출 시 재생성됨.
    if metaPath.exists():
        metaPath.unlink()

    if showProgress:
        _log.info(
            "[%s] 완료: ok=%d no_body=%d error=%d (처리 %d), 전체 %d행, %.1fMB",
            period,
            okCount,
            noBodyCount,
            errorCount,
            len(targets),
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


# ═══════════════════════════════════════════
# HF 동기화 (push / lazy pull)
# ═══════════════════════════════════════════

# 다운로드 1 회 시도 가드 (period 또는 "_ALL_") — 실패 시 무한 retry 회피.
_HF_DOWNLOAD_ATTEMPTED: set[str] = set()


def pushAllFilings(periods: list[str] | None = None, *, token: str | None = None) -> int:
    """allFilings parquet 을 HF dataset 에 **단일 commit 배치**로 업로드.

    파일당 `upload_file`(= 파일당 commit)은 HF 무료플랜 **128 commit/hr** 한도를
    때려 대량 백필 push 가 partial 로 잘린다(reconcile 203일 → 128 성공 사고). 그래서
    pipeline `hfUpload` 와 동일하게 `create_commit` 배치(300 files/commit, `retryHfCall`
    로 429·LFS-RuntimeError 백오프)로 commit 수를 1~수 개로 줄인다. 같은 경로 파일은
    자동 덮어쓰기(HF Hub commit-based).

    Args:
        periods: 업로드 일자 list (YYYYMMDD). None 이면 로컬 `data/dart/allFilings/`
            에 있는 모든 `.parquet` (정기 `*_meta.parquet` 제외).
        token: HF token. None 이면 env `HF_TOKEN`.

    Returns:
        int — 업로드 성공 파일 수(성공 commit 에 포함된 파일 합).

    Raises:
        없음 — 배치 commit 실패는 warning 로그 후 다음 배치 진행(멱등 — 다음 reconcile 이어감).

    Example:
        >>> pushAllFilings(["20260527", "20260528"], token=os.environ["HF_TOKEN"])  # doctest: +SKIP
    """
    import os as _os

    hfToken = token or _os.environ.get("HF_TOKEN", "")
    if not hfToken:
        _log.warning("[HF↑] HF_TOKEN 없음 — 업로드 skip")
        return 0

    outDir = _allFilingsDir()
    if periods is None:
        files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
    else:
        files = [outDir / f"{p}.parquet" for p in periods]
        files = [f for f in files if f.exists()]

    if not files:
        _log.info("[HF↑] 업로드 대상 0")
        return 0

    from huggingface_hub import CommitOperationAdd, HfApi

    from dartlab.core.dataConfig import repoFor
    from dartlab.core.hfRetry import retryHfCall

    relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    repo = repoFor(_ALLFILINGS_DIR_KEY)
    api = HfApi(token=hfToken)

    batchSize = 300  # hfUpload 와 동일 — commit 당 파일 수 상한(128 commit/hr 한도 회피)
    total = (len(files) + batchSize - 1) // batchSize
    ok = 0
    for i in range(0, len(files), batchSize):
        batch = files[i : i + batchSize]
        n = i // batchSize + 1
        ops = [CommitOperationAdd(path_in_repo=f"{relDir}/{f.name}", path_or_fileobj=str(f)) for f in batch]
        try:
            retryHfCall(
                api.create_commit,
                repo_id=repo,
                repo_type="dataset",
                operations=ops,
                commit_message=f"allFilings push: {len(batch)} files ({n}/{total})",
            )
            ok += len(batch)
            _log.info("[HF↑] %d/%d 파일 commit (배치 %d/%d)", ok, len(files), n, total)
        except Exception as exc:  # noqa: BLE001 — 배치 실패 격리(멱등, 다음 reconcile 이어감)
            _log.warning("[HF↑] 배치 %d/%d (%d 파일) 실패: %s", n, total, len(batch), exc)
    _log.info("[HF↑] 완료: %d/%d 파일", ok, len(files))
    return ok


def _ensureFromHf(period: str | None = None) -> bool:
    """artifact 부재 시 HF dataset 에서 lazy 다운로드.

    panel sync `_ensureFromHf` 동일 패턴 — `huggingface_hub.snapshot_download`
    로 `{HF_REPO}:dart/allFilings/` 의 parquet 받음.

    Args:
        period: 특정 일자만 (YYYYMMDD) 받기. None 이면 디렉토리 전체.

    Returns:
        bool — 다운로드 성공 (또는 이미 로컬에 있음).

    Raises:
        없음 — 네트워크 / 인증 / 부재 실패는 warning 로그 후 False.

    환경변수 `DARTLAB_NO_HF_DOWNLOAD=1` 시 즉시 skip. 한 (period or "_ALL_") 1 회만 시도.
    """
    import os as _os

    outDir = _allFilingsDir()
    if period is not None:
        if (outDir / f"{period}.parquet").exists():
            return True

    if _os.environ.get("DARTLAB_NO_HF_DOWNLOAD", "").strip() in ("1", "true", "True"):
        return False

    key = period or "_ALL_"
    if key in _HF_DOWNLOAD_ATTEMPTED:
        return False
    _HF_DOWNLOAD_ATTEMPTED.add(key)

    try:
        from huggingface_hub import snapshot_download

        from dartlab.core.dataConfig import repoFor
        from dartlab.core.hfRetry import retryHfCall

        relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
        pattern = f"{relDir}/{period}.parquet" if period else f"{relDir}/*.parquet"
        retryHfCall(  # HF read SSOT(core.hfRetry) — 429/503/504 단일 백오프
            snapshot_download,
            repo_id=repoFor(_ALLFILINGS_DIR_KEY),
            repo_type="dataset",
            allow_patterns=[pattern],
            local_dir=str(Path(_cfg.dataDir)),
        )
        return True
    except Exception as exc:  # noqa: BLE001
        _log.warning("[HF↓] allFilings 다운로드 실패 (%s): %s", period or "ALL", exc)
        return False


def _remoteDates(*, token: str | None = None) -> set[str]:
    """HF dataset 에 올라간 allFilings **본문** parquet 의 일자(YYYYMMDD) 집합.

    reconcile 의 "HF 가 가진 일자" 쪽. ``list_repo_tree`` scoped 열거(retryHfCall)로
    ``dart/allFilings/`` prefix 만 읽어 전체 dataset metadata 폭주(429)를 피한다.
    ``_meta``(목록만) parquet 은 제외 — 본문 완료(``{YYYYMMDD}.parquet``)만 SSOT.

    Args:
        token: HF 토큰. None 이면 env ``HF_TOKEN``.

    Returns:
        set[str] — 본문 완료 일자 집합 (예: ``{"20260603", "20260604"}``). HF 호출
        실패(네트워크/인증/부재)면 빈 set.

    Raises:
        없음 — 모든 예외는 warning 로그 후 빈 set 으로 흡수.

    Example:
        >>> _remoteDates()  # doctest: +SKIP
        {'20260601', '20260602'}
    """
    import os as _os

    tok = token or _os.environ.get("HF_TOKEN") or None
    relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    try:
        from huggingface_hub import HfApi

        from dartlab.core.dataConfig import repoFor
        from dartlab.core.hfRetry import retryHfCall

        api = HfApi(token=tok)

        def _listTree() -> list:
            return list(
                api.list_repo_tree(
                    repo_id=repoFor(_ALLFILINGS_DIR_KEY),
                    path_in_repo=relDir,
                    repo_type="dataset",
                    recursive=False,
                    token=tok,
                )
            )

        entries = retryHfCall(_listTree)
    except Exception as exc:  # noqa: BLE001 — 원격 목록 실패는 빈 set(로컬 우선 fallback)
        _log.warning("[HF] allFilings 원격 목록 조회 실패: %s", exc)
        return set()

    dates: set[str] = set()
    for item in entries:
        rel = getattr(item, "path", "") or getattr(item, "rfilename", "")
        name = Path(str(rel)).name
        stem = name[:-8] if name.endswith(".parquet") else ""  # ".parquet" = 8자
        if len(stem) == 8 and stem.isdigit():
            dates.add(stem)
    return dates


def _pullDates(dates: list[str], *, token: str | None = None) -> int:
    """지정 일자들의 본문 parquet 을 HF→로컬 1회 snapshot_download(retry).

    reconcile 의 pull 방향 헬퍼 — 일자별 개별 호출 대신 ``allow_patterns`` 리스트로
    한 번에 받는다. tmp→rename atomic 은 huggingface_hub 가 보장.

    Args:
        dates: 받을 일자 list (YYYYMMDD).
        token: HF 토큰. None 이면 env ``HF_TOKEN``.

    Returns:
        int — 실제로 로컬에 떨어진(존재 확인) 일자 수. 빈 입력/실패면 0.

    Raises:
        없음 — HF 실패는 warning 후 0.

    Example:
        >>> _pullDates(["20260601", "20260602"])  # doctest: +SKIP
        2
    """
    if not dates:
        return 0

    import os as _os

    tok = token or _os.environ.get("HF_TOKEN") or None
    relDir = DATA_RELEASES[_ALLFILINGS_DIR_KEY]["dir"]
    try:
        from huggingface_hub import snapshot_download

        from dartlab.core.dataConfig import repoFor
        from dartlab.core.hfRetry import retryHfCall

        retryHfCall(
            snapshot_download,
            repo_id=repoFor(_ALLFILINGS_DIR_KEY),
            repo_type="dataset",
            allow_patterns=[f"{relDir}/{d}.parquet" for d in dates],
            local_dir=str(Path(_cfg.dataDir)),
            token=tok,
        )
    except Exception as exc:  # noqa: BLE001 — pull 실패는 격리(다음 reconcile 자연 회복)
        _log.warning("[HF↓] allFilings reconcile pull 실패 (%d일): %s", len(dates), exc)
        return 0

    outDir = _allFilingsDir()
    return sum(1 for d in dates if (outDir / f"{d}.parquet").exists())


def reconcileAllFilings(
    *,
    pull: bool = True,
    push: bool = True,
    token: str | None = None,
) -> dict:
    """로컬 ↔ HF allFilings parquet **양방향 reconcile** — 집합 차분, 부족분만 채움.

    로컬 본문 완료 일자(``collectedDates``)와 HF 일자(``_remoteDates``)를 비교해:
        - **HF 가 앞섬**(HF 에만 있는 일자) → ``pull`` 이면 로컬로 다운로드.
        - **로컬이 앞섬**(로컬에만 있는 일자) → ``push`` 이면 HF 로 업로드.
    양쪽을 합집합으로 수렴시킨다. 이미 양쪽에 있는 일자는 건드리지 않는다(idempotent).

    Args:
        pull: HF→로컬 (HF 가 앞선 일자 다운로드).
        push: 로컬→HF (로컬이 앞선 일자 업로드).
        token: HF 토큰. None 이면 env ``HF_TOKEN``.

    Returns:
        dict — ``{"localBefore", "remoteBefore", "pullDates", "pushDates", "pulled",
        "pushed", "localAfter", "inSync"}``. ``inSync`` 는 활성 방향 기준 처리 대상 0 여부.

    Raises:
        없음 — HF 호출 실패는 _remoteDates/_pullDates/pushAllFilings 내부에서 격리.

    Example:
        >>> reconcileAllFilings()  # doctest: +SKIP
        {'localBefore': 225, 'remoteBefore': 230, 'pulled': 5, 'pushed': 0, ...}

    Guide:
        - 운영자 로컬 머신용 — 로컬 store 가 영속인 곳에서 의미. CI ephemeral runner 는
          pull 이 전 이력 재다운로드라 무의미(daily forward+push job 이 CI 최신화 담당).
        - 월 단위 백필 후 push 로 새 일자 HF 반영, 다른 머신/CI 가 수집한 일자는 pull 로 로컬 보강.
    """
    localDates = set(collectedDates())
    remoteDates = _remoteDates(token=token)

    pullDates = sorted(remoteDates - localDates) if pull else []
    pushDates = sorted(localDates - remoteDates) if push else []

    pulledN = _pullDates(pullDates, token=token)
    pushedN = pushAllFilings(pushDates, token=token) if pushDates else 0

    return {
        "localBefore": len(localDates),
        "remoteBefore": len(remoteDates),
        "pullDates": pullDates,
        "pushDates": pushDates,
        "pulled": pulledN,
        "pushed": pushedN,
        "localAfter": len(collectedDates()),
        "inSync": not pullDates and not pushDates,
    }


def loadDay(period: str) -> pl.DataFrame | None:
    """수집된 하루치 데이터 로드. 로컬 부재 시 HF 에서 lazy 다운로드.

    Args:
        period: YYYYMMDD.

    Raises:
        없음.

    Example:
        >>> loadDay("20260527")  # doctest: +SKIP

    Returns:
        pl.DataFrame 또는 None — 수집 결과.
    """
    path = _allFilingsDir() / f"{period}.parquet"
    if not path.exists():
        _ensureFromHf(period)
    if not path.exists():
        return None
    return pl.read_parquet(path)


@withMemoryBudget(limitMb=500)
def loadAll() -> pl.DataFrame:
    """원문 수집 완료된 전체 데이터 로드. 로컬 디렉토리 비어있으면 HF 에서 lazy 다운로드.

    Args:
        (인자 자동 생성).

    Raises:
        없음.

    Example:
        >>> loadAll()  # doctest: +SKIP

    Returns:
        pl.DataFrame — 결과.
    """
    outDir = _allFilingsDir()
    files = sorted(f for f in outDir.glob("*.parquet") if _META_SUFFIX not in f.stem)
    if not files:
        _ensureFromHf()
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
