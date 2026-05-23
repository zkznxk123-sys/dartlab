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
from pathlib import Path

import polars as pl

import dartlab.config as _cfg

_DOCS_DIR_REL = "dart/docs"
_SECTIONS_CACHE_REL = "dart/sectionsCache"


def _docsPath(stockCode: str) -> Path:
    return Path(_cfg.dataDir) / _DOCS_DIR_REL / f"{stockCode}.parquet"


def _topicsHash(topics: frozenset[str] | None) -> str:
    """topics → 6 char hex hash. None = 전체 (key 'all')."""
    if topics is None:
        return "all"
    return hashlib.blake2b(",".join(sorted(topics)).encode("utf-8"), digest_size=3).hexdigest()


def diskCachePath(stockCode: str, topics: frozenset[str] | None) -> Path:
    """sections() 결과 cache parquet 경로. topics None = 전체."""
    suffix = _topicsHash(topics)
    return Path(_cfg.dataDir) / _SECTIONS_CACHE_REL / f"{stockCode}_{suffix}.parquet"


def isDiskCacheFresh(stockCode: str, topics: frozenset[str] | None) -> bool:
    """디스크 캐시가 docs.parquet 보다 새로우면 True."""
    cachePath = diskCachePath(stockCode, topics)
    if not cachePath.exists():
        return False
    docsPath = _docsPath(stockCode)
    if not docsPath.exists():
        return True  # docs 없으면 cache 만 신뢰
    return cachePath.stat().st_mtime > docsPath.stat().st_mtime


def loadDiskCache(stockCode: str, topics: frozenset[str] | None) -> pl.DataFrame | None:
    """디스크 캐시 read. miss 또는 stale 이면 None."""
    if not isDiskCacheFresh(stockCode, topics):
        return None
    try:
        return pl.read_parquet(diskCachePath(stockCode, topics))
    except Exception:
        return None


def saveDiskCache(
    stockCode: str,
    topics: frozenset[str] | None,
    result: pl.DataFrame | None,
) -> None:
    """build 결과 디스크 캐시 저장. None 결과는 저장 X (next build 가 다시 시도)."""
    if result is None or result.is_empty():
        return
    cachePath = diskCachePath(stockCode, topics)
    cachePath.parent.mkdir(parents=True, exist_ok=True)
    try:
        # snappy compression — 빠른 write + 적당한 압축률
        result.write_parquet(cachePath, compression="snappy")
    except Exception:
        # 디스크 쓰기 실패 시 silent fail — in-memory cache 만 활용
        pass


def clearDiskCache(stockCode: str | None = None) -> None:
    """디스크 캐시 해제. stockCode=None 이면 전체 폴더 삭제.

    Args:
        stockCode: 특정 종목 cache 만 해제. None = 전체.
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
