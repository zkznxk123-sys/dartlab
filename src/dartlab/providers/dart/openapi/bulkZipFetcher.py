"""DART document.xml 원본 zip 병렬 수집 — 본진 모듈.

DartClient 의 _KeySlot 풀이 키별 throttle + 020 cooldown 자동 마이그레이션 처리.
본 모듈은 ThreadPoolExecutor + atomic file write (`.tmp` → rename) 만 책임.

사용자 (2026-05-22): "병렬호출 안전하게 받는 로직을 본진에만들고 동시호출해라
서로 간섭없이 그리고 안전저장 그리고 키제한됐을때 다른 키로이관하는 로직까지"

- 간섭 0: DartClient._acquireSlot/_releaseSlot lock 으로 키 예약 → 스레드 충돌 0
- 안전 저장: `.zip.tmp` 쓰고 rename (POSIX/NTFS 모두 atomic 보장)
- 020 마이그레이션: getBytes 안에서 cooldown slot 자동 회피 + 다른 slot 재선택

호출 예:
    from dartlab.providers.dart.openapi.client import DartClient
    from dartlab.providers.dart.openapi.bulkZipFetcher import fetchZipsParallel
    client = DartClient()
    stats = fetchZipsParallel(
        client,
        [("005930", "20240514001234"), ...],
        outDir=Path("data/dart/original/docs"),
    )
"""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from dartlab.providers.dart.openapi.client import DartClient

_MIN_VALID_BYTES = 1000


@dataclass
class FetchStats:
    """수집 통계 — 스레드 안전 (lock 보호)."""

    saved: int = 0
    skipped: int = 0
    failed: int = 0
    bytesTotal: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, *, saved: int = 0, skipped: int = 0, failed: int = 0, bytesTotal: int = 0) -> None:
        """카운터 증가 — 스레드 안전 (lock 보호). worker 가 매 결과마다 호출."""
        with self._lock:
            self.saved += saved
            self.skipped += skipped
            self.failed += failed
            self.bytesTotal += bytesTotal

    def asDict(self) -> dict[str, int]:
        """현재 통계 snapshot dict — 진행 표시 용 (lock 안 atomic 읽기)."""
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
    except Exception:
        stats.add(failed=1)


def fetchZipsParallel(
    client: DartClient,
    targets: list[tuple[str, str]],
    *,
    outDir: Path,
    workers: int | None = None,
    progressEvery: int = 100,
    progressCallback=None,
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
    """
    if not targets:
        return FetchStats()
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
