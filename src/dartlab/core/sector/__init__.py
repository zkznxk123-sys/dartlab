"""WICS 섹터 분류 — industry/compat.py에 위임.

하위 호환용 shim. 모든 실제 구현은 dartlab.industry.compat.
"""

from dartlab.industry import (
    IndustryGroup,
    MarketParams,
    Sector,
    SectorInfo,
    SectorParams,
    classify,
    getMarketParams,
    getParams,
)

__all__ = [
    "classify",
    "getParams",
    "getMarketParams",
    "IndustryGroup",
    "MarketParams",
    "Sector",
    "SectorInfo",
    "SectorParams",
]
