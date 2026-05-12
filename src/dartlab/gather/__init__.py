"""Gather 엔진 — 통합 멀티소스 비동기 병렬 수집.

thin facade. 본체는 `engine.py` 의 Gather 클래스. 모듈-level 싱글턴
`getDefaultGather()` 는 `entry.py` 에 정의 (룰 4 thin).

Usage::

    from dartlab.gather import Gather, getDefaultGather

    g = getDefaultGather()           # 싱글턴
    g.price("005930")               # OHLCV 1년
    g.macro()                       # 거시지표 wide
    snap = g.collect("005930")      # 병렬 수집 스냅샷

모든 공개 API는 동기 시그니처. 내부적으로 asyncio 병렬 실행.
"""

from __future__ import annotations

from .engine import Gather
from .entry import getDefaultGather
from .types import (
    FlowData,
    GatherResult,
    GatherSnapshot,
    InsiderTrade,
    InstitutionOwnership,
    MajorHolder,
    MarketSnapshot,
    NewsItem,
    PeerData,
    PriceSnapshot,
    RevenueConsensus,
    SectorInfo,
    SourceUnavailableError,
)

__all__ = [
    "FlowData",
    "Gather",
    "GatherResult",
    "GatherSnapshot",
    "InsiderTrade",
    "InstitutionOwnership",
    "MajorHolder",
    "MarketSnapshot",
    "NewsItem",
    "PeerData",
    "PriceSnapshot",
    "RevenueConsensus",
    "SectorInfo",
    "SourceUnavailableError",
    "getDefaultGather",
]
