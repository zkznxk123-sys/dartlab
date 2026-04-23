"""industry/sector — 하위 호환 re-export shim.

섹터 타입·파라미터·classify 로직의 실제 원본은 `dartlab.core.sector` (L0 SSOT).
이 모듈은 기존 `from dartlab.industry.sector import Sector, ...` 경로 호환용.

L2 엔진 로직(산업 매핑 파이프라인)은 `dartlab.industry.build`·`industry.taxonomy` 에.
"""

from __future__ import annotations

from dartlab.core.sector import (
    MARKET_KR as MARKET_KR,
)
from dartlab.core.sector import (
    MARKET_PARAMS as MARKET_PARAMS,
)
from dartlab.core.sector import (
    MARKET_US as MARKET_US,
)
from dartlab.core.sector import (
    IndustryGroup as IndustryGroup,
)
from dartlab.core.sector import (
    MarketParams as MarketParams,
)
from dartlab.core.sector import (
    Sector as Sector,
)
from dartlab.core.sector import (
    SectorInfo as SectorInfo,
)
from dartlab.core.sector import (
    SectorParams as SectorParams,
)
from dartlab.core.sector import (
    _byValue as _byValue,
)
from dartlab.core.sector import (
    _loadSectorData as _loadSectorData,
)
from dartlab.core.sector import (
    _loadThresholds as _loadThresholds,
)
from dartlab.core.sector import (
    _matchProductKeywords as _matchProductKeywords,
)
from dartlab.core.sector import (
    classify as classify,
)
from dartlab.core.sector import (
    getMarketParams as getMarketParams,
)
from dartlab.core.sector import (
    getParams as getParams,
)
from dartlab.core.sector import (
    getThresholds as getThresholds,
)
