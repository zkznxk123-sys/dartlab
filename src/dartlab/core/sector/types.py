"""섹터 분류 데이터 타입 — industry/compat.py에서 re-export.

이 모듈은 하위 호환용 shim이다. 실제 구현은 dartlab.industry.compat.
"""

from dartlab.industry.compat import (
    MARKET_KR,
    MARKET_PARAMS,
    MARKET_US,
    IndustryGroup,
    MarketParams,
    Sector,
    SectorInfo,
    SectorParams,
    getMarketParams,
)

__all__ = [
    "IndustryGroup",
    "MarketParams",
    "Sector",
    "SectorInfo",
    "SectorParams",
    "getMarketParams",
    "MARKET_KR",
    "MARKET_US",
    "MARKET_PARAMS",
]
