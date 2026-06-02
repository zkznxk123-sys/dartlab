"""HuggingFace HTTP 429/503/504 공용 retry helper.

HF 무료 플랜 commit 한도 128/hour — 초과 시 응답 본문에
`"retry this action in X minutes"` 를 돌려준다. 본문 파싱 우선, Retry-After
헤더 2순위, exponential fallback 3순위로 실제 서버 권장 대기시간을 존중.

사용 예::

    from _hfRetry import retryHfCall
    retryHfCall(api.create_commit, repo_id=..., operations=..., ...)
    retryHfCall(api.upload_file, path_or_fileobj=..., ...)
    retryHfCall(api.upload_folder, folder_path=..., ...)
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

_RETRYABLE_STATUS = {429, 503, 504}
_BACKOFF_SECONDS_FALLBACK = (60, 300, 900, 1200)  # 60s + 5m + 15m + 20m = 41m
_MAX_SINGLE_WAIT = 1800  # 한 번 backoff 최대 30분
_RETRY_MIN_RE = re.compile(r"retry this action in (\d+)\s*minutes?", re.IGNORECASE)
_RETRY_SEC_RE = re.compile(r"retry this action in (\d+)\s*seconds?", re.IGNORECASE)
# LFS 멀티스레드 업로드(_upload_lfs_files)는 transient(429/S3/네트워크) 실패를 RuntimeError
# "Error while uploading 'X' to the Hub." 로 감싼다 — HfHubHTTPError 가 아니라 과거 재시도 0번이었다.
# 실제 원인은 __cause__ 또는 메시지로 식별해 동일 백오프로 재시도(create_commit 대량 LFS 배치 강건화).
_TRANSIENT_MSG_RE = re.compile(
    r"error while uploading|timed out|timeout|connection|temporarily|throttl|rate.?limit|too many requests",
    re.IGNORECASE,
)


def _isRetryable(exc: Exception) -> bool:
    """transient(재시도 가치) 여부 — 직접 429/503/504, 또는 LFS 래핑 RuntimeError(원인 429·메시지 transient)."""
    from huggingface_hub.errors import HfHubHTTPError

    if isinstance(exc, HfHubHTTPError):
        return getattr(getattr(exc, "response", None), "status_code", None) in _RETRYABLE_STATUS
    cause = getattr(exc, "__cause__", None)
    if isinstance(cause, HfHubHTTPError):
        if getattr(getattr(cause, "response", None), "status_code", None) in _RETRYABLE_STATUS:
            return True
    return bool(_TRANSIENT_MSG_RE.search(str(exc)))


def parseRetryWait(exc: Exception, attempt: int) -> int:
    """HF 응답에서 권장 대기시간 (초) 추출.

    Priority:
        1. response.headers['Retry-After'] (RFC 표준)
        2. 메시지 본문 "retry this action in X minutes/seconds" (HF 관례)
        3. _BACKOFF_SECONDS_FALLBACK[attempt] (고정 fallback)

    Returns
    -------
    int
        대기 초 (_MAX_SINGLE_WAIT 로 clamp).
    """
    response = getattr(exc, "response", None)
    if response is not None and hasattr(response, "headers"):
        retryAfter = response.headers.get("Retry-After")
        if retryAfter:
            try:
                return min(int(retryAfter), _MAX_SINGLE_WAIT)
            except ValueError:
                pass

    msg = str(exc)
    m = _RETRY_MIN_RE.search(msg)
    if m:
        return min(int(m.group(1)) * 60 + 30, _MAX_SINGLE_WAIT)  # +30s 여유
    m = _RETRY_SEC_RE.search(msg)
    if m:
        return min(int(m.group(1)) + 10, _MAX_SINGLE_WAIT)

    if attempt < len(_BACKOFF_SECONDS_FALLBACK):
        return _BACKOFF_SECONDS_FALLBACK[attempt]
    return _BACKOFF_SECONDS_FALLBACK[-1]


def retryHfCall(fn: Callable[..., Any], *args, **kwargs) -> Any:
    """HF API 호출을 transient 백오프로 감싼다.

    재시도 대상: (1) HfHubHTTPError 429/503/504, (2) LFS 업로드 래핑
    RuntimeError("Error while uploading ...") 처럼 원인이 429 이거나 메시지가
    transient 인 경우. 그 외(인증·400 등 fatal)는 즉시 raise.

    Parameters
    ----------
    fn : Callable
        api.create_commit · api.upload_file · api.upload_folder 등.

    Returns
    -------
    Any
        fn 의 정상 반환값.
    """
    attempts = len(_BACKOFF_SECONDS_FALLBACK) + 1
    for attempt in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — _isRetryable 가 transient 만 선별, 나머지 즉시 raise
            if not _isRetryable(exc) or attempt == attempts - 1:
                raise
            wait = parseRetryWait(exc, attempt)
            label = getattr(getattr(exc, "response", None), "status_code", None) or type(exc).__name__
            print(
                f"[hfRetry] HF {label} on {fn.__name__} — {wait}s 후 재시도 ({attempt + 1}/{attempts - 1})",
                flush=True,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")
