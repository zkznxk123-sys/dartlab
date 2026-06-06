"""섹터 분류 + 밸류에이션 파라미터 — L1.5 진입점.

본 진입점은 thin re-export. 본체 (Enum · dataclass · classify · params · thresholds) 는
`dartlab.core.sector`. sectorParams.json / thresholds.json 데이터 파일은 `dartlab/industry/` 위치.
"""

from __future__ import annotations

from dartlab.core.sector import (
    MARKET_KR,
    MARKET_PARAMS,
    MARKET_US,
    IndustryGroup,
    MarketParams,
    Sector,
    SectorInfo,
    SectorParams,
    classify,
    getMarketParams,
    getParams,
    getSectorParamsByName,
    getThresholds,
)

__all__ = [
    "Sector",
    "IndustryGroup",
    "SectorInfo",
    "SectorParams",
    "MarketParams",
    "MARKET_KR",
    "MARKET_US",
    "MARKET_PARAMS",
    "classify",
    "getParams",
    "getSectorParamsByName",
    "getMarketParams",
    "getThresholds",
]
