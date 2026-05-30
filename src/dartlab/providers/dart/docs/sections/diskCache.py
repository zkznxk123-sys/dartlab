"""[deprecated] sections() 결과 디스크 캐시 — plan snazzy-wibbling-origami 폐기.

옛 시스템 (sections artifact 부재 환경) 의 runtime build cache. 신 시스템은 zip ingest
시점 1 회 영속화 (``data/dart/sections/{code}/{period}.parquet`` 신 SSOT) 가 자체
영속화 — runtime cache 무의미.

본 모듈의 모든 함수는 no-op (호환 stub). 호출자 변경 없이 sectionsCache 디렉터리
0 (사용자 워크스페이스 청결).
"""

from __future__ import annotations

import logging

import polars as pl

_log = logging.getLogger(__name__)


def saveDiskCache(stockCode: str, topics, result: pl.DataFrame) -> None:
    """[deprecated] no-op — sections artifact 가 자체 영속화.

    Args:
        stockCode, topics, result: 옛 시그니처 호환용. 모두 무시된다.

    Returns:
        None — 항상.

    Example:
        >>> saveDiskCache("005930", [], pl.DataFrame()) is None
        True

    Raises:
        없음 — no-op.
    """
    return None


def loadDiskCache(stockCode: str, topics) -> pl.DataFrame | None:
    """[deprecated] no-op — sections artifact mmap 0.07s 가 충분히 빠름.

    Args:
        stockCode, topics: 옛 시그니처 호환용. 무시된다.

    Returns:
        None — 항상 (cache miss 로 동작).

    Example:
        >>> loadDiskCache("005930", []) is None
        True

    Raises:
        없음 — no-op.
    """
    return None


def savePreparedDiskCache(stockCode: str, periodRowsDf: pl.DataFrame, validPeriods: list, teacherTopics: dict) -> None:
    """[deprecated] no-op — sections artifact 가 자체 영속화.

    Args:
        stockCode, periodRowsDf, validPeriods, teacherTopics: 옛 시그니처 호환용. 무시된다.

    Returns:
        None — 항상.

    Example:
        >>> savePreparedDiskCache("005930", pl.DataFrame(), [], {}) is None
        True

    Raises:
        없음 — no-op.
    """
    return None


def loadPreparedDiskCache(stockCode: str):
    """[deprecated] no-op — sections artifact mmap 이 prepared cache 역할 대신.

    Args:
        stockCode: 옛 시그니처 호환용. 무시된다.

    Returns:
        None — 항상 (cache miss 로 동작).

    Example:
        >>> loadPreparedDiskCache("005930") is None
        True

    Raises:
        없음 — no-op.
    """
    return None


def diskCachePath(stockCode: str, topics):
    """[deprecated] no-op stub. sectionsCache 디렉터리 생성 0.

    Args:
        stockCode, topics: 옛 시그니처 호환용. 무시된다.

    Returns:
        None — 항상 (경로 미생성).

    Example:
        >>> diskCachePath("005930", []) is None
        True

    Raises:
        없음 — no-op.
    """
    return None


def isDiskCacheFresh(stockCode: str, topics) -> bool:
    """[deprecated] 항상 False — cache 자체 폐기.

    Args:
        stockCode, topics: 옛 시그니처 호환용. 무시된다.

    Returns:
        False — 항상 (cache 폐기로 신선도 없음).

    Example:
        >>> isDiskCacheFresh("005930", [])
        False

    Raises:
        없음 — no-op.
    """
    return False
