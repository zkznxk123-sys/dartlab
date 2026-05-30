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
    """[deprecated] no-op — sections artifact 가 자체 영속화."""
    return None


def loadDiskCache(stockCode: str, topics) -> pl.DataFrame | None:
    """[deprecated] no-op — sections artifact mmap 0.07s 가 충분히 빠름."""
    return None


def savePreparedDiskCache(stockCode: str, periodRowsDf: pl.DataFrame, validPeriods: list, teacherTopics: dict) -> None:
    """[deprecated] no-op — sections artifact 가 자체 영속화."""
    return None


def loadPreparedDiskCache(stockCode: str):
    """[deprecated] no-op — sections artifact mmap 이 prepared cache 역할 대신."""
    return None


def diskCachePath(stockCode: str, topics):
    """[deprecated] no-op stub. sectionsCache 디렉터리 생성 0."""
    return None


def isDiskCacheFresh(stockCode: str, topics) -> bool:
    """[deprecated] 항상 False — cache 자체 폐기."""
    return False
