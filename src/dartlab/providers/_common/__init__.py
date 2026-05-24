"""providers/_common/ — DART / EDGAR / EDINET 공통 helper (T9-1 stage 2).

stage 1 scaffold + stage 2 (현재) — 첫 실 helper (httpRetry) 이전.

이전 완료:
    - httpRetry(): 외부 API 호출 retry 로직 (지수 backoff)

분해 진척:
    Stage 1 ✓ — scaffold
    Stage 2 (현재) — httpRetry 이전
    Stage 3 — XBRL 공통 helper
    Stage 4 — docs zip 처리
    Stage 5-7 — lazy import + importlinter contract + 27 게이트 검증

분해 후 목표:
    providers/dart/ ≤ 30K
    providers/edgar/ ≤ 25K
    providers/edinet/ ≤ 5K (현재)
    providers/_common/ ≤ 15K
    합산 ≤ 75K (현재 104K, -28 percent)
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def httpRetry(
    fn: Callable[[], T],
    *,
    maxRetries: int = 3,
    backoffSec: float = 1.0,
    backoffMultiplier: float = 2.0,
) -> T:
    """외부 API 호출 retry — 지수 backoff (T9-1).

    Capabilities:
        DART / EDGAR / EDINET / FRED 등 외부 API 호출의 transient 실패 (네트워크
        / rate limit / 5xx) 자동 재시도. dart/openapi 와 edgar/openapi 의
        중복 retry 로직을 통합.

    Args:
        fn: 0-arg callable.
        maxRetries: 최대 재시도 횟수 (기본 3).
        backoffSec: 첫 backoff 초 (기본 1).
        backoffMultiplier: 매 재시도 multiplier (기본 2).

    Returns:
        fn() 결과.

    Example:
        >>> from dartlab.providers._common import httpRetry
        >>> result = httpRetry(lambda: fetchSomething())

    AIContext:
        T9-1 providers 분해 첫 공통 helper.

    Raises:
        마지막 시도의 exception.
    """
    lastException: Exception | None = None
    currentBackoff = backoffSec
    for attempt in range(maxRetries + 1):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            lastException = e
            if attempt >= maxRetries:
                break
            time.sleep(currentBackoff)
            currentBackoff *= backoffMultiplier
    raise lastException if lastException else RuntimeError("httpRetry: 알 수 없는 실패")


__all__ = ["httpRetry"]
