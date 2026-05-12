"""Gather 도메인 레지스트리 — fallback 순서 + 도메인 모듈 lazy loader.

thin facade. 실제 정의는 `fallback.py`. 호출자는 본 패키지의 공개 심볼
(`PRICE_FALLBACK`, `loadDomain` 등) 만 사용한다.
"""

from __future__ import annotations

from .fallback import (
    CONSENSUS_FALLBACK,
    DIVIDENDS_FALLBACK,
    FLOW_FALLBACK,
    HISTORY_FALLBACK,
    PRICE_FALLBACK,
    getPriceFallback,
    loadDomain,
)

__all__ = [
    "CONSENSUS_FALLBACK",
    "DIVIDENDS_FALLBACK",
    "FLOW_FALLBACK",
    "HISTORY_FALLBACK",
    "PRICE_FALLBACK",
    "getPriceFallback",
    "loadDomain",
]
