"""SEC 분기별 Financial Statement Data Sets 벌크 다운로더 (fetch 전담).

URL 패턴: https://www.sec.gov/files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip
주기: 분기별, 분기말 +2~3개월에 공개. 크기: 60~130MB.

⛔ 규칙: num.txt 는 받지 않는다 — 수치값(val) 원본은 companyfacts.zip (매일).
분기 zip 에서 필요한 것은 meta 정보(sub/pre/tag)뿐.

본 모듈은 **수집(Extract) 전담** — zip download + 최신분기 탐색만. TSV 파싱·parquet
변환(Transform)·로컬 조회(Load)는 ``providers/edgar/bulk/datasetBulk.py``. providers
build 가 zip 이 필요하면 ``core.edgarClient.downloadQuarterlyDataset`` DIP 로 본 fetch 호출.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

from dartlab.core.edgarBulkFreshness import (
    isBulkFresh,
    readSavedEtag,
    touchBulkFreshness,
)

_log = logging.getLogger(__name__)

_BASE_URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets"
_LANDING_URL = "https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets"
_UA = "dartlab eddmpython@gmail.com"

_DEFAULT_TIMEOUT = httpx.Timeout(60.0, read=None, write=60.0, connect=30.0)


# ── 경로 헬퍼 ─────────────────────────────────────────────────────────


def _bulkDir() -> Path:
    from dartlab.core.dataLoader import _getDataRoot

    d = _getDataRoot() / "edgar" / "_bulk" / "quarterly"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _quarterTag(year: int, quarter: int) -> str:
    return f"quarterly_{year}Q{quarter}"


def _datasetUrl(year: int, quarter: int) -> str:
    return f"{_BASE_URL}/{year}q{quarter}.zip"


# ── 다운로드 ─────────────────────────────────────────────────────────


def _headDataset(year: int, quarter: int) -> httpx.Response | None:
    """분기 zip 존재 여부 HEAD. 404 면 None, 200 이면 Response."""
    url = _datasetUrl(year, quarter)
    headers = {"User-Agent": _UA, "Accept-Encoding": "identity"}
    try:
        with httpx.Client(timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
            resp = client.head(url, follow_redirects=True)
    except httpx.HTTPError as exc:
        _log.warning("dataset %sQ%s HEAD 실패: %s", year, quarter, exc)
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        _log.warning("dataset %sQ%s HEAD status=%s", year, quarter, resp.status_code)
        return None
    return resp


def discoverLatestQuarter(maxYear: int | None = None) -> tuple[int, int] | None:
    """SEC 에 공개된 최신 분기를 HEAD 요청으로 탐색.

    maxYear=None 이면 현재 연도까지 체크. 공개된 (year, quarter) 튜플 반환.
    분기말 +2~3개월 지연이 있으므로 일반적으로 현재 분기-1 이 최신.

    Args:
        maxYear: 탐색 상한 연도 (None 이면 현재).

    Returns:
        ``(year, quarter)`` tuple 또는 None.

    Raises:
        없음.

    Example:
        >>> discoverLatestQuarter()
    """
    if maxYear is None:
        maxYear = datetime.now(timezone.utc).year

    # 최신 → 과거 순으로 체크, 최초 200 응답에서 멈춤
    for year in range(maxYear, maxYear - 3, -1):
        for quarter in (4, 3, 2, 1):
            # 미래 분기는 건너뜀
            qEnd = date(year, quarter * 3, 1)
            if qEnd > date.today():
                continue
            resp = _headDataset(year, quarter)
            if resp is not None:
                return year, quarter
    return None


def downloadQuarterlyDataset(
    year: int,
    quarter: int,
    *,
    force: bool = False,
    ttlHours: int = 24 * 30,
) -> Path | None:
    """``{Y}q{Q}.zip`` 다운로드. 존재하지 않으면 None.

    분기 벌크는 한 번 공개 후 변동이 적으므로 기본 TTL 30 일.

    Args:
        year: 연도.
        quarter: 분기 (1~4).
        force: 캐시 무시.
        ttlHours: 신선도 TTL.

    Returns:
        다운로드된 zip Path 또는 None (해당 분기 부재).

    Raises:
        없음 (httpx 예외는 잡아서 None 반환).

    Example:
        >>> downloadQuarterlyDataset(2024, 3)
    """
    tag = _quarterTag(year, quarter)
    zipPath = _bulkDir() / f"{year}q{quarter}.zip"

    if not force and zipPath.exists() and isBulkFresh(tag, ttlHours=ttlHours):
        return zipPath

    url = _datasetUrl(year, quarter)
    headers = {"User-Agent": _UA, "Accept-Encoding": "identity"}

    savedEtag = readSavedEtag(tag)
    with httpx.Client(timeout=_DEFAULT_TIMEOUT, headers=headers) as client:
        try:
            head = client.head(url, follow_redirects=True)
        except httpx.HTTPError as exc:
            _log.warning("dataset %sq%s HEAD 실패: %s", year, quarter, exc)
            return None
        if head.status_code == 404:
            return None
        if head.status_code >= 400:
            _log.warning("dataset %sq%s status=%s — 스킵", year, quarter, head.status_code)
            return None

        remoteEtag = head.headers.get("ETag", "").strip('"')
        remoteLen = int(head.headers.get("Content-Length", "0") or 0)

        if (
            not force
            and savedEtag
            and remoteEtag
            and savedEtag == remoteEtag
            and zipPath.exists()
            and zipPath.stat().st_size == remoteLen
        ):
            touchBulkFreshness(tag, etag=remoteEtag)
            return zipPath

        _log.info("dataset %sq%s 다운로드 (%.1f MB)", year, quarter, remoteLen / 1024 / 1024)
        tmpPath = zipPath.with_suffix(".zip.tmp")
        with client.stream("GET", url, follow_redirects=True) as resp:
            resp.raise_for_status()
            with tmpPath.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
        tmpPath.replace(zipPath)
        touchBulkFreshness(tag, etag=remoteEtag)
        return zipPath


__all__ = [
    "discoverLatestQuarter",
    "downloadQuarterlyDataset",
]
