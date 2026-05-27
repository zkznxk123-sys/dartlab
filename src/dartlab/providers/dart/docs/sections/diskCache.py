"""sections() 결과 디스크 캐시 — Phase 3.

In-memory `_sectionsResultCache` (Phase 2) 는 프로세스 종료 시 사라짐. 매 프로세스
시작 후 첫 build 가 6-8s 소요 (cold).

본 모듈은 build 결과를 `data/dart/sections/{stockCode}_{topicsHash}.parquet` 로
저장 + freshness check 로 invalidation. 같은 종목 다회 호출 + 다른 프로세스 시작
시에도 0.3s 정도로 read 가능.

Freshness rule:
- `docs/{stockCode}.parquet` 가 cache 보다 새로우면 → cache stale, rebuild
- topics 변경 시 → 별도 cache key

사용자 (2026-05-23):
"sections만드는시간이 8초인데 더줄일수는 없을까" — 첫 빌드 6s, 이후 0.3s 목표.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_log = logging.getLogger(__name__)

_DOCS_DIR_REL = "dart/docs"
_SECTIONS_CACHE_REL = "dart/sectionsCache"
# Phase 1 (_PreparedRows) disk cache — Phase 3 (final wide DF) 의 *상위* 캐시.
# 같은 종목 다른 topics 부분 호출 시 Phase 3 가 miss 면 본 cache 가 XML parsing
# 11s + 421MB peak 우회 (mmap IPC + tiny JSON).
_PREPARED_CACHE_REL = "dart/sectionsCache"  # 같은 폴더, suffix 로 구분


def _docsPath(stockCode: str) -> Path:
    return Path(_cfg.dataDir) / _DOCS_DIR_REL / f"{stockCode}.parquet"


def _topicsHash(topics: frozenset[str] | None) -> str:
    """topics → 6 char hex hash. None = 전체 (key 'all')."""
    if topics is None:
        return "all"
    return hashlib.blake2b(",".join(sorted(topics)).encode("utf-8"), digest_size=3).hexdigest()


def diskCachePath(stockCode: str, topics: frozenset[str] | None) -> Path:
    """sections() 결과 cache parquet 경로. topics None = 전체.

    Args:
        stockCode: 종목코드 (6 자리).
        topics: 부분 topic 집합 또는 None (전체).

    Returns:
        ``data/dart/sectionsCache/{stockCode}_{suffix}.parquet`` 경로 (suffix
        는 topics hash 또는 ``"all"``).

    Raises:
        없음.

    Example:
        >>> diskCachePath("005930", None).name
        '005930_all.parquet'
    """
    suffix = _topicsHash(topics)
    return Path(_cfg.dataDir) / _SECTIONS_CACHE_REL / f"{stockCode}_{suffix}.parquet"


def isDiskCacheFresh(stockCode: str, topics: frozenset[str] | None) -> bool:
    """디스크 캐시가 docs.parquet 보다 새로우면 True.

    Args:
        stockCode: 종목코드.
        topics: 부분 topic 집합 또는 None.

    Returns:
        cache 가 존재 + docs.parquet 보다 mtime 새로움 시 True.
        cache 부재 → False. docs 부재 → True (cache 만 신뢰).

    Raises:
        없음.

    Example:
        >>> isDiskCacheFresh("005930", None)
        True
    """
    cachePath = diskCachePath(stockCode, topics)
    if not cachePath.exists():
        return False
    docsPath = _docsPath(stockCode)
    if not docsPath.exists():
        return True  # docs 없으면 cache 만 신뢰
    return cachePath.stat().st_mtime > docsPath.stat().st_mtime


def loadDiskCache(stockCode: str, topics: frozenset[str] | None) -> pl.DataFrame | None:
    """디스크 캐시 read. miss 또는 stale 이면 None.

    corrupt parquet (부분 write 후 crash 잔재) 는 ``OSError`` / Polars 에러 →
    None 반환 + warning 로깅. caller 가 rebuild 진행. 옛 broken cache 는
    다음 ``saveDiskCache`` 가 overwrite.

    Args:
        stockCode: 종목코드.
        topics: 부분 topic 집합 또는 None.

    Returns:
        DataFrame (hit + fresh) 또는 None (miss / stale / corrupt).

    Raises:
        없음 — 모든 IO 에러는 warning + None 으로 변환.

    Example:
        >>> loadDiskCache("005930", None)  # doctest: +SKIP
    """
    if not isDiskCacheFresh(stockCode, topics):
        return None
    cachePath = diskCachePath(stockCode, topics)
    try:
        return pl.read_parquet(cachePath)
    except (OSError, pl.exceptions.ComputeError, pl.exceptions.ShapeError) as exc:
        _log.warning("sections diskCache 읽기 실패: %s — rebuild 진행 (%s)", cachePath.name, exc)
        return None


def saveDiskCache(
    stockCode: str,
    topics: frozenset[str] | None,
    result: pl.DataFrame | None,
) -> None:
    """build 결과 디스크 캐시 저장. None 결과는 저장 X (next build 가 다시 시도).

    write 실패 (디스크 full / permission denied / corrupt cache dir) 시 warning
    로깅 + in-memory cache 만 활용. silent fail 은 다음 프로세스 재시작 시
    반복 cold build (~6s) 의 원인이라 명시 노출.

    Args:
        stockCode: 종목코드.
        topics: 부분 topic 집합 또는 None.
        result: build 결과 DataFrame. None / 빈 DataFrame 이면 저장 skip.

    Returns:
        None.

    Raises:
        없음 — IO 에러는 warning + 무시.

    Example:
        >>> saveDiskCache("005930", None, df)  # doctest: +SKIP
    """
    if result is None or result.is_empty():
        return
    cachePath = diskCachePath(stockCode, topics)
    cachePath.parent.mkdir(parents=True, exist_ok=True)
    try:
        # snappy compression — 빠른 write + 적당한 압축률
        result.write_parquet(cachePath, compression="snappy")
    except (OSError, pl.exceptions.ComputeError) as exc:
        _log.warning("sections diskCache 쓰기 실패: %s (%s) — in-memory only", cachePath.name, exc)


def clearDiskCache(stockCode: str | None = None) -> None:
    """디스크 캐시 해제. stockCode=None 이면 전체 폴더 삭제.

    Args:
        stockCode: 특정 종목 cache 만 해제. None = 전체.

    Raises:
        없음 — OSError 는 무시 (best effort 삭제).

    Example:
        >>> clearDiskCache("005930")  # 005930 종목의 모든 topic hash cache 삭제
    """
    cacheDir = Path(_cfg.dataDir) / _SECTIONS_CACHE_REL
    if not cacheDir.exists():
        return
    if stockCode is None:
        # 전체 삭제 (다음 build 시 자동 재생성)
        for p in cacheDir.glob("*.parquet"):
            try:
                p.unlink()
            except OSError:
                pass
    else:
        # 해당 stockCode prefix 의 모든 topic hash cache 삭제
        for p in cacheDir.glob(f"{stockCode}_*.parquet"):
            try:
                p.unlink()
            except OSError:
                pass


# ── Phase 1 (_PreparedRows) disk cache ──
# periodRowsDf (polars DF, 50~100MB) + validPeriods (list[str]) + teacherTopics
# (dict[str,str]). docs.parquet mtime 변경 시 stale → rebuild.


def preparedCachePath(stockCode: str) -> tuple[Path, Path]:
    """_PreparedRows disk cache 경로 — (arrow IPC, json sidecar) tuple.

    arrow IPC mmap → periodRowsDf 의 polars DF zero-copy load. sidecar JSON 은
    validPeriods + teacherTopics + docs_mtime 메타.

    Args:
        stockCode: 종목코드 (6 자리).

    Returns:
        (arrow_path, json_path) tuple.

    Example:
        >>> preparedCachePath("005930")[0].name
        '005930_prepared.arrow'
    """
    base = Path(_cfg.dataDir) / _PREPARED_CACHE_REL
    return (base / f"{stockCode}_prepared.arrow", base / f"{stockCode}_prepared.json")


def loadPreparedDiskCache(stockCode: str):
    """``_PreparedRows`` disk cache read. miss / stale / corrupt → None.

    docs.parquet mtime > arrow mtime 이면 stale (rebuild 필요). mmap memory_map=True
    로 RSS 위임 → 다중 process 공유 + page cache 활용. caller 는 본 함수 결과를
    ``_PreparedRows`` instance 로 받아 in-memory LRU 에 박는다.

    Args:
        stockCode: 종목코드.

    Returns:
        ``(periodRowsDf, validPeriods, teacherTopics)`` tuple 또는 None.

    Example:
        >>> loadPreparedDiskCache("005930")  # doctest: +SKIP
    """
    arrowPath, jsonPath = preparedCachePath(stockCode)
    if not arrowPath.exists() or not jsonPath.exists():
        return None
    docsPath = _docsPath(stockCode)
    if docsPath.exists() and docsPath.stat().st_mtime > arrowPath.stat().st_mtime:
        return None
    try:
        meta = json.loads(jsonPath.read_text(encoding="utf-8"))
        periodRowsDf = pl.read_ipc(str(arrowPath), memory_map=True)
        validPeriods: list[str] = list(meta.get("validPeriods") or [])
        rawTeacher = meta.get("teacherTopics") or {}
        # 저장 시 set → list 직렬화. caller (pipeline._getPrepared) 는 set 형이
        # 자연스러우니 list 인 값들을 set 으로 복원. scalar (str) 값은 그대로.
        teacherTopics: dict[str, object] = {k: (set(v) if isinstance(v, list) else v) for k, v in rawTeacher.items()}
        return (periodRowsDf, validPeriods, teacherTopics)
    except (OSError, ValueError, json.JSONDecodeError, pl.exceptions.ComputeError) as exc:
        _log.warning("preparedDiskCache read 실패 %s — rebuild (%s)", stockCode, exc)
        return None


def savePreparedDiskCache(
    stockCode: str,
    periodRowsDf: pl.DataFrame,
    validPeriods: list[str],
    teacherTopics: dict[str, str],
) -> None:
    """``_PreparedRows`` disk cache write. write 실패 = silent warn + in-memory only.

    arrow IPC + sidecar JSON 2 파일 atomic-ish write. 실패 시 cache 누락이 다음
    process restart 의 11s cold rebuild 로 잠재화 — 명시 노출 위해 warning 로깅.

    Args:
        stockCode: 종목코드.
        periodRowsDf: Phase 1 결과 polars DF (모든 period × topic row + _periodKey).
        validPeriods: sorted period list (annual + Q1/Q2/Q3).
        teacherTopics: chapter→topic 매핑 (first annual 기준).

    Example:
        >>> savePreparedDiskCache("005930", df, periods, teacher)  # doctest: +SKIP
    """
    if periodRowsDf is None or periodRowsDf.is_empty():
        return
    arrowPath, jsonPath = preparedCachePath(stockCode)
    arrowPath.parent.mkdir(parents=True, exist_ok=True)
    # teacherTopics 의 값이 set 인 경우 (chapter → topic 후보 집합) JSON 직렬화 불가 →
    # list 로 정규화. load 시 caller 가 다시 set 으로 변환할 책임 (현재 caller 는
    # in-place 사용이라 list/set 둘 다 동작).
    teacherSerializable = {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in teacherTopics.items()}
    try:
        periodRowsDf.write_ipc(str(arrowPath), compression="zstd")
        jsonPath.write_text(
            json.dumps(
                {"validPeriods": validPeriods, "teacherTopics": teacherSerializable},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except (OSError, ValueError, pl.exceptions.ComputeError) as exc:
        _log.warning("preparedDiskCache write 실패 %s (%s) — in-memory only", stockCode, exc)


def clearPreparedDiskCache(stockCode: str | None = None) -> None:
    """``_PreparedRows`` disk cache 해제. stockCode=None 이면 전체.

    Args:
        stockCode: 특정 종목 prepared cache 만 해제. None = 전체.

    Example:
        >>> clearPreparedDiskCache("005930")
    """
    cacheDir = Path(_cfg.dataDir) / _PREPARED_CACHE_REL
    if not cacheDir.exists():
        return
    pattern = f"{stockCode}_prepared.*" if stockCode else "*_prepared.*"
    for p in cacheDir.glob(pattern):
        try:
            p.unlink()
        except OSError:
            pass


def _buildOneForBatch(code: str) -> tuple[str, bool]:
    """ProcessPool worker — 단일 corp sections build 후 디스크 캐시 자동 저장.

    Returns:
        (code, success_bool).
    """
    try:
        from dartlab.providers.dart import Company

        sec = Company(code).sections
        return (code, sec is not None and not sec.is_empty())
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        _log.warning("buildBatchParallel(%s) 실패: %s", code, exc)
        return (code, False)


def buildBatchParallel(
    codes: list[str],
    *,
    workers: int | None = None,
) -> dict[str, bool]:
    """N corps 의 sections 병렬 build (ProcessPoolExecutor) — 결과 디스크 캐시 저장.

    각 process 가 1 corp 씩 build → 디스크 cache 저장. 후속 호출 (다른 process /
    같은 process 둘 다) 은 디스크 cache hit 으로 ~1.3s.

    POC 검증 (2026-05-23): 5 baseline 직렬 61s → 병렬 5 worker 19s = 3.25× speedup.

    Args:
        codes: 종목코드 list (예 ["005930", "000660", ...]).
        workers: ProcessPool worker 수. None = min(len(codes), os.cpu_count()).

    Returns:
        dict[code, bool] — 각 corp 의 build 성공 여부.

    Raises:
        없음 — worker 별 예외는 (code, False) 로 변환.

    Example:
        >>> from dartlab.providers.dart.docs.sections.diskCache import buildBatchParallel
        >>> results = buildBatchParallel(["005930", "035720", "005380"])
        >>> # 후속 Company('005930').sections 는 디스크 cache hit (~1.3s)
    """
    import os
    from concurrent.futures import ProcessPoolExecutor

    if not codes:
        return {}
    if workers is None:
        workers = min(len(codes), os.cpu_count() or 4)
    results: dict[str, bool] = {}
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for code, ok in ex.map(_buildOneForBatch, codes):
            results[code] = ok
    return results
