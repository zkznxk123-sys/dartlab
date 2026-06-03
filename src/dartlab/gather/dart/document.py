"""DART document.xml 원본 zip 병렬 수집 — 본진 모듈.

DartClient 의 _KeySlot 풀이 키별 throttle + 020 cooldown 자동 마이그레이션 처리.
본 모듈은 ThreadPoolExecutor + atomic file write (`.tmp` → rename) 만 책임.

사용자 (2026-05-22): "병렬호출 안전하게 받는 로직을 본진에만들고 동시호출해라
서로 간섭없이 그리고 안전저장 그리고 키제한됐을때 다른 키로이관하는 로직까지"

- 간섭 0: DartClient._acquireSlot/_releaseSlot lock 으로 키 예약 → 스레드 충돌 0
- 안전 저장: `.zip.tmp` 쓰고 rename (POSIX/NTFS 모두 atomic 보장)
- 020 마이그레이션: getBytes 안에서 cooldown slot 자동 회피 + 다른 slot 재선택

호출 예:
    # 저수준 — (code, rceptNo) 페어 직접 지정
    from dartlab.gather.dart.document import fetchZipsParallel
    client = DartClient()
    stats = fetchZipsParallel(client, [("005930", "20240514001234"), ...],
                              outDir=Path("data/original/dart/docs"))

    # 고수준 — 전체 종목 일괄 (docs.parquet 의 rcept 자동 수집)
    from dartlab.gather.dart.document import collectAllOriginalZips
    stats = collectAllOriginalZips()   # data/dart/docs/*.parquet 모든 종목
    stats = collectAllOriginalZips(codes=["005930", "000660"])  # 일부
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import dartlab.config as _cfg
from dartlab.gather.dart.client import DartClient

_MIN_VALID_BYTES = 1000
_DOCS_DIR_REL = "dart/docs"
_ORIGINAL_DOCS_DIR_REL = "original/dart/docs"


@dataclass
class FetchStats:
    """수집 통계 — 스레드 안전 (lock 보호)."""

    saved: int = 0
    skipped: int = 0
    failed: int = 0
    bytesTotal: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, *, saved: int = 0, skipped: int = 0, failed: int = 0, bytesTotal: int = 0) -> None:
        """카운터 증가 — 스레드 안전 (lock 보호). worker 가 매 결과마다 호출.

        Args:
            saved: 저장 성공 카운트 delta.
            skipped: 이미 존재로 skip 카운트 delta.
            failed: 실패 카운트 delta.
            bytesTotal: 누적 바이트 delta.

        Returns:
            None.

        Raises:
            없음.

        Example:
            >>> stats = FetchStats()
            >>> stats.add(saved=1, bytesTotal=12345)
        """
        with self._lock:
            self.saved += saved
            self.skipped += skipped
            self.failed += failed
            self.bytesTotal += bytesTotal

    def asDict(self) -> dict[str, int]:
        """현재 통계 snapshot dict — 진행 표시 용 (lock 안 atomic 읽기).

        Returns:
            ``{"saved": int, "skipped": int, "failed": int, "bytesTotal": int}``.

        Raises:
            없음.

        Example:
            >>> FetchStats().asDict()
            {'saved': 0, 'skipped': 0, 'failed': 0, 'bytesTotal': 0}
        """
        with self._lock:
            return {
                "saved": self.saved,
                "skipped": self.skipped,
                "failed": self.failed,
                "bytesTotal": self.bytesTotal,
            }


def safeWriteBytes(path: Path, data: bytes) -> None:
    """동시 쓰기 안전 — `.tmp` 쓰고 os.replace (atomic rename).

    동일 path 동시 쓰기 시: 마지막 rename 만 보임. 부분 파일·읽기 중 충돌 0.
    `.tmp` suffix 에 thread id + monotonic ns 박아 두 스레드가 같은 tmp 노리는 사고 차단.

    Args:
        path: 최종 저장 경로 (parent dir 자동 생성).
        data: 저장할 바이트.

    Returns:
        None.

    Raises:
        OSError: 디스크 full / permission denied / 잘못된 경로.

    Example:
        >>> safeWriteBytes(Path("/tmp/out.bin"), b"...")  # doctest: +SKIP
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tag = f"{threading.get_ident()}.{time.monotonic_ns()}"
    tmp = path.with_suffix(path.suffix + f".tmp.{tag}")
    tmp.write_bytes(data)
    os.replace(tmp, path)  # Windows + POSIX atomic


def _fetchOne(
    client: DartClient,
    code: str,
    rceptNo: str,
    outDir: Path,
    stats: FetchStats,
) -> None:
    outCode = outDir / code
    outPath = outCode / f"{rceptNo}.zip"
    if outPath.exists() and outPath.stat().st_size > _MIN_VALID_BYTES:
        stats.add(skipped=1)
        return
    try:
        raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
        if not raw or len(raw) < _MIN_VALID_BYTES:
            stats.add(failed=1)
            return
        safeWriteBytes(outPath, raw)
        stats.add(saved=1, bytesTotal=len(raw))
    except (OSError, RuntimeError, ValueError):
        # DartApiError(network/rate-limit) + 디스크 IO 실패 — 카운트 후 다음 종목 진행.
        stats.add(failed=1)


def fetchZipsParallel(
    client: DartClient,
    targets: list[tuple[str, str]],
    *,
    outDir: Path,
    workers: int | None = None,
    progressEvery: int = 100,
    progressCallback=None,
    limit: int = 0,
) -> FetchStats:
    """N (code, rceptNo) → outDir/{code}/{rceptNo}.zip 병렬 저장.

    Parameters
    ----------
    client : DartClient
        스레드 안전 키 풀 (본진 client.py 의 _KeySlot 기반).
    targets : list[tuple[str, str]]
        (stockCode, rceptNo) 목록. 중복 안 거름 — caller 책임.
    outDir : Path
        baseline 디렉토리. 안에 {code}/ subdir 자동 생성.
    workers : int | None
        ThreadPoolExecutor 워커 수. None = len(slots) — 각 키 1 스레드 default.
    progressEvery : int
        N 개마다 progressCallback 호출.
    progressCallback : callable | None
        (done, total, statsDict) → None. 진행 표시용.

    Raises:
        없음 — 개별 fetch 실패는 stats.failed 로 변환.

    Example:
        >>> fetchZipsParallel(client, [("005930", "..."), ...], outDir=Path("/tmp"))  # doctest: +SKIP
    """
    if not targets:
        return FetchStats()
    if limit > 0:
        targets = targets[:limit]
    if workers is None:
        workers = len(client._slots)
    stats = FetchStats()
    outDir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetchOne, client, code, rceptNo, outDir, stats) for code, rceptNo in targets]
        done = 0
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if progressCallback and done % progressEvery == 0:
                progressCallback(done, len(targets), stats.asDict())
        if progressCallback:
            progressCallback(len(targets), len(targets), stats.asDict())
    return stats


def iterZipsParallel(
    client: DartClient,
    targets: list[tuple[str, str]],
    *,
    outDir: Path,
    workers: int | None = None,
) -> "Iterator[tuple[str, str, bool, int]]":
    """``fetchZipsParallel`` 의 streaming pair — 결과 row 1 개씩 yield.

    Args:
        client: ``DartClient``.
        targets: ``[(stockCode, rceptNo), ...]``.
        outDir: 저장 디렉토리.
        workers: ThreadPoolExecutor 워커 수.

    Yields:
        ``(stockCode, rceptNo, ok, bytesWritten)`` — ok=True 면 저장 성공.

    Raises:
        없음 — 개별 fetch 실패는 ok=False.

    Example:
        >>> for code, rcept, ok, n in iterZipsParallel(client, targets, outDir=Path("/tmp")):
        ...     pass  # doctest: +SKIP
    """
    if not targets:
        return
    if workers is None:
        workers = len(client._slots)
    outDir.mkdir(parents=True, exist_ok=True)

    def _fetchAndReport(code: str, rceptNo: str) -> tuple[str, str, bool, int]:
        outCode = outDir / code
        outPath = outCode / f"{rceptNo}.zip"
        if outPath.exists() and outPath.stat().st_size > _MIN_VALID_BYTES:
            return code, rceptNo, True, outPath.stat().st_size
        try:
            raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
            if not raw or len(raw) < _MIN_VALID_BYTES:
                return code, rceptNo, False, 0
            safeWriteBytes(outPath, raw)
            return code, rceptNo, True, len(raw)
        except (OSError, RuntimeError, ValueError):
            return code, rceptNo, False, 0

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetchAndReport, code, rceptNo) for code, rceptNo in targets]
        for fut in as_completed(futures):
            yield fut.result()


def streamZipBytes(
    client: DartClient,
    targets: list[tuple[str, str]],
    *,
    workers: int | None = None,
) -> "Iterator[tuple[str, str, bytes]]":
    """``iterZipsParallel`` 의 메모리 쌍둥이 — (code, rceptNo, zipBytes) yield, 디스크 저장 0.

    online 1패스 panel 빌드 전용: document.xml API 결과를 파일로 안 쓰고 bytes 그대로 흘려
    gather ``buildPanelFromStream`` 이 메모리에서 14-col parquet 화. ``data/original/dart/docs``
    에 zip 을 만들지 않는다 (로컬 전용 zip 우회). 실패·미달(_MIN_VALID_BYTES)은 yield 생략.

    메모리 가드: 호출측은 **종목 단위로 끊어** 호출(전 종목 targets 한 번에 X) — 동시 in-flight
    bytes 를 workers × zip크기로 bound (Q4 대형 zip 폭주 방지).

    Args:
        client: ``DartClient`` (스레드 안전 키 풀, 020 cooldown 자동 마이그레이션).
        targets: ``[(stockCode, rceptNo), ...]`` (한 종목 단위 권장).
        workers: ThreadPoolExecutor 워커 수. None = len(client._slots).

    Yields:
        ``(stockCode, rceptNo, zipBytes)`` — 유효 zip 만 (실패/미달 skip).

    Raises:
        없음 — 개별 fetch 실패는 yield 생략.

    Example:
        >>> for code, rcept, raw in streamZipBytes(client, [("005930", "...")]):
        ...     pass  # doctest: +SKIP

    SeeAlso:
        - ``iterZipsParallel`` — 디스크 저장 버전(메타 yield).
        - ``buildTargetsFromDocsParquet`` — (code, rceptNo) targets 생산.
        - gather ``buildPanelFromStream`` — 본 bytes 스트림을 14-col parquet 화.

    Requires:
        - ``DartClient`` (DART_API_KEYS). concurrent.futures.

    Capabilities:
        - online 1패스 — zip 디스크 저장 없이 document.xml bytes 를 메모리 스트림으로 흘림.

    Guide:
        - layer-밖 sync entry(onlinePanel.py)가 종목 단위로 호출 — gather build 와 조합.

    AIContext:
        - 유효 zip 만 yield (실패/미달 skip) — 호출측은 즉시 소비 후 bytes 폐기(메모리 bound).

    When:
        - online 1패스 panel 빌드가 신규/변경 rcept 를 디스크 zip 없이 받을 때.

    How:
        - ThreadPool(getBytes document.xml) → 유효(_MIN_VALID_BYTES) zip bytes as_completed yield.

    LLM Specifications:
        AntiPatterns:
            - 전 종목 targets 한 번에 호출 금지 — 종목 단위(bytes 메모리 폭주 가드).
            - 디스크 저장 금지 — 메모리 1패스(iterZipsParallel 이 디스크 버전).
        OutputSchema:
            - ``Iterator[tuple[str, str, bytes]]`` (유효 zip 만).
        Prerequisites:
            - DartClient. targets (code, rceptNo).
        Freshness:
            - 매 호출 fetch (증분 신규 rcept).
        Dataflow:
            - targets → ThreadPool getBytes → 유효 bytes yield.
        TargetMarkets:
            - KR (DART document.xml).
    """
    if not targets:
        return
    if workers is None:
        workers = len(client._slots)

    def _fetchBytes(code: str, rceptNo: str) -> "tuple[str, str, bytes] | None":
        try:
            raw = client.getBytes("document.xml", {"rcept_no": rceptNo})
            if not raw or len(raw) < _MIN_VALID_BYTES:
                return None
            return code, rceptNo, raw
        except (OSError, RuntimeError, ValueError):
            return None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_fetchBytes, code, rceptNo) for code, rceptNo in targets]
        for fut in as_completed(futures):
            res = fut.result()
            if res is not None:
                yield res


def buildTargetsFromDocsParquet(
    codes: Iterable[str] | None = None,
    *,
    docsDir: Path | None = None,
) -> list[tuple[str, str]]:
    """data/dart/docs/{code}.parquet 의 rcept_no → (code, rceptNo) 페어 list.

    Args:
        codes: 대상 종목 코드 (None = docs 디렉토리의 전체 parquet).
        docsDir: docs.parquet 디렉토리. None = ``{dataDir}/dart/docs``.

    Returns:
        ``[(stockCode, rceptNo), ...]`` 페어 list (중복 제거 + parquet 부재 시 skip).

    Raises:
        없음 — 개별 parquet 읽기 실패는 skip.

    Example:
        >>> buildTargetsFromDocsParquet(codes=["005930"])  # doctest: +SKIP
    """
    import polars as pl

    docsDir = docsDir or (Path(_cfg.dataDir) / _DOCS_DIR_REL)
    if codes is None:
        codes = sorted(p.stem for p in docsDir.glob("*.parquet"))
    targets: list[tuple[str, str]] = []
    for code in codes:
        parquet = docsDir / f"{code}.parquet"
        if not parquet.exists():
            continue
        try:
            df = pl.read_parquet(parquet, columns=["rcept_no"])
        except (OSError, pl.exceptions.ComputeError):
            continue
        for r in df.select("rcept_no").unique().to_series().to_list():
            targets.append((code, str(r)))
    return targets


def collectAllOriginalZips(
    codes: Iterable[str] | None = None,
    *,
    client: DartClient | None = None,
    docsDir: Path | None = None,
    outDir: Path | None = None,
    workers: int = 4,
    progressEvery: int = 500,
    progressCallback: Callable[[int, int, dict[str, int]], None] | None = None,
) -> FetchStats:
    """전체 종목 (또는 지정 codes) 의 원본 zip 일괄 수집.

    DART per-IP anti-abuse 회피를 위해 ``DartClient._acquireSlot`` 가 sequential
    exhausted 패턴 (키 1개로 580 rpm 소진 후 다음 키) 사용. workers=4 = finance
    수집의 ``asyncio.Semaphore(4)`` 패턴 동일.

    Args:
        codes: 대상 종목 코드 (None = data/dart/docs/*.parquet 의 모든 종목).
        client: DartClient (None = 환경변수 키로 자동 생성).
        docsDir: docs.parquet 디렉토리. None = ``{dataDir}/dart/docs``.
        outDir: zip 출력 디렉토리. None = ``{dataDir}/original/dart/docs``.
        workers: ThreadPoolExecutor 워커 수. default 4 (finance 패턴).
        progressEvery: N 페어 마다 progressCallback 호출.
        progressCallback: (done, total, statsDict) → None. 진행 표시.

    Returns:
        FetchStats — saved/skipped/failed/bytesTotal.

    Raises:
        없음 — 개별 fetch 실패는 stats.failed 로 변환.

    Example:
        >>> collectAllOriginalZips(codes=["005930"])  # doctest: +SKIP
    """
    outDir = outDir or (Path(_cfg.dataDir) / _ORIGINAL_DOCS_DIR_REL)
    if client is None:
        client = DartClient()
    targets = buildTargetsFromDocsParquet(codes=codes, docsDir=docsDir)
    return fetchZipsParallel(
        client,
        targets,
        outDir=outDir,
        workers=workers,
        progressEvery=progressEvery,
        progressCallback=progressCallback,
    )
