"""Remote freshness and HF download helpers for ``core.dataLoader``."""

from __future__ import annotations

import os
import socket
import time
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


def _noRefreshEnv() -> bool:
    """``DARTLAB_NO_REFRESH=1`` 시 HF refresh 우회."""
    return os.environ.get("DARTLAB_NO_REFRESH") == "1"


def downloadWithRetry(
    url: str,
    dest: Path,
    *,
    maxRetries: int,
    socketTimeout,
    urlretrieve,
) -> None:
    """URL → dest 다운로드. 실패 시 지수 backoff로 재시도한다."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    lastErr = None
    token = os.environ.get("HF_TOKEN", "").strip()
    for attempt in range(maxRetries):
        try:
            with socketTimeout():
                if token:
                    req = Request(url)
                    req.add_header("Authorization", f"Bearer {token}")
                    with urlopen(req) as resp, tmp.open("wb") as f:
                        while chunk := resp.read(1 << 20):
                            f.write(chunk)
                else:
                    urlretrieve(url, tmp)  # tmp 로 받고 atomic rename — 중단 시 손상 dest 미생성
            tmp.replace(dest)
            return
        except (URLError, socket.timeout, OSError) as exc:
            lastErr = exc
            if tmp.exists():
                tmp.unlink()
            if attempt < maxRetries - 1:
                time.sleep(2 ** (attempt + 1))
    raise lastErr


def checkRemoteFreshness(
    stockCode: str,
    localPath: Path,
    category: str,
    *,
    hfBaseUrl: Callable[[str], str],
    fetchRemoteEtagAndSize: Callable[[str], tuple[str, int]],
) -> bool | None:
    """로컬 파일이 원격보다 오래됐는지 ETag와 크기로 확인한다."""
    hfUrl = f"{hfBaseUrl(category)}/{stockCode}.parquet"
    etagPath = localPath.with_suffix(".parquet.etag")
    try:
        remoteEtag, remoteSize = fetchRemoteEtagAndSize(hfUrl)
        if not remoteEtag:
            return None
        if remoteSize > 0 and localPath.exists():
            try:
                if localPath.stat().st_size != remoteSize:
                    return True
            except OSError:
                pass
        if etagPath.exists():
            localEtag = etagPath.read_text(encoding="utf-8").strip()
            return remoteEtag != localEtag
        return True
    except (URLError, socket.timeout, OSError, ValueError):
        return None


def saveEtag(
    stockCode: str,
    dest: Path,
    category: str,
    *,
    hfBaseUrl: Callable[[str], str],
    fetchRemoteEtag: Callable[[str], str],
) -> None:
    """다운로드 성공 후 HF ETag를 사이드카 파일에 저장한다."""
    hfUrl = f"{hfBaseUrl(category)}/{stockCode}.parquet"
    etagPath = dest.with_suffix(".parquet.etag")
    try:
        etag = fetchRemoteEtag(hfUrl)
        if etag:
            etagPath.write_text(etag, encoding="utf-8")
    except (URLError, socket.timeout, OSError):
        pass


def maybeWarnStale(path: Path, *, warnedPaths: set[str], staleWarnDays: int) -> None:
    """오래된 로컬 데이터 경고를 세션당 경로별 1회만 보낸다."""
    key = str(path)
    if key in warnedPaths:
        return
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return
    ageDays = int(age // 86400)
    if ageDays >= staleWarnDays:
        warnedPaths.add(key)
        try:
            from dartlab.core.messaging import emit

            emit("data:stale_warning", ageDays=ageDays)
        except ImportError:
            pass


def shouldRefreshDart(
    path: Path,
    refresh: str,
    *,
    staleWarnDays: int,
    dartFreshnessTtlHours: int,
    warnStale: Callable[[Path], None],
) -> bool:
    """DART 카테고리 로컬 파일의 갱신 필요 여부를 판단한다."""
    if _noRefreshEnv():
        return False
    if refresh == "local_only":
        return False
    if refresh == "force_check":
        return True
    etagPath = path.with_suffix(".parquet.etag")
    if not etagPath.exists():
        try:
            age = time.time() - path.stat().st_mtime
            if age > staleWarnDays * 86400:
                warnStale(path)
            return age > dartFreshnessTtlHours * 3600 * 7
        except OSError:
            return False
    try:
        age = time.time() - etagPath.stat().st_mtime
        if age > staleWarnDays * 86400:
            warnStale(etagPath)
        return age > dartFreshnessTtlHours * 3600
    except OSError:
        return False


def shouldRefreshHfCategory(
    path: Path,
    category: str,
    refresh: str,
    *,
    krxFreshnessTtlHours: int,
    shouldRefreshDartFunc: Callable[[Path, str], bool],
) -> bool:
    """HF 공개 parquet 카테고리별 freshness 정책."""
    if _noRefreshEnv():
        return False
    if category not in {"krxPrices", "krxIndices", "govPrices", "govPriceCompany", "govIndices", "govIndexPerIndex"}:
        return shouldRefreshDartFunc(path, refresh)
    if refresh == "local_only":
        return False
    if refresh == "force_check":
        return True
    etagPath = path.with_suffix(".parquet.etag")
    if not etagPath.exists():
        return True
    try:
        age = time.time() - etagPath.stat().st_mtime
        return age > krxFreshnessTtlHours * 3600
    except OSError:
        return True


def refreshFromHf(
    stockCode: str,
    path: Path,
    category: str,
    *,
    dataReleases: dict,
    hfBaseUrl: Callable[[str], str],
    checkRemoteFreshness: Callable[[str, Path, str], bool | None],
    downloadWithRetry: Callable[[str, Path], None],
    saveEtag: Callable[[str, Path, str], None],
) -> None:
    """ETag 비교 후 HF가 최신이면 다운로드로 갱신하고 실패 시 기존 파일을 유지한다."""
    stale = checkRemoteFreshness(stockCode, path, category)
    if stale is None:
        etagPath = path.with_suffix(".parquet.etag")
        if etagPath.exists():
            etagPath.touch()
        return
    if stale is not True:
        etagPath = path.with_suffix(".parquet.etag")
        if etagPath.exists():
            etagPath.touch()
        return
    from dartlab.core.messaging import emit

    label = dataReleases[category]["label"]
    tmpPath = path.with_suffix(".tmp")
    try:
        emit("download:start", stockCode=stockCode, label=label)
        hfUrl = f"{hfBaseUrl(category)}/{stockCode}.parquet"
        downloadWithRetry(hfUrl, tmpPath)
        tmpPath.replace(path)
        saveEtag(stockCode, path, category)
        size = path.stat().st_size
        sizeStr = f"{size / 1024:.0f}KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f}MB"
        emit("download:done_short", sizeStr=sizeStr)
    except (URLError, socket.timeout, OSError) as exc:
        if tmpPath.exists():
            tmpPath.unlink()
        emit("download:failed_single", stockCode=stockCode, label=label, error=str(exc))


__all__ = [
    "checkRemoteFreshness",
    "downloadWithRetry",
    "maybeWarnStale",
    "refreshFromHf",
    "saveEtag",
    "shouldRefreshDart",
    "shouldRefreshHfCategory",
]
