"""섹터별 밸류에이션 파라미터 — re-export from core.sector.__init__ + 하위 호환 dict 재구성.

하위 호환: 기존 `from dartlab.frame.sector.params import SECTOR_PARAMS, INDUSTRY_GROUP_PARAMS, getParams` 경로 유지.
실제 정의는 `dartlab.frame.sector.__init__`.
"""

from dartlab.frame.sector import (
    IndustryGroup,
    Sector,
    SectorParams,
    _byValue,
    _loadSectorData,
    getMarketParams,
    getParams,
)

# 하위 호환: SECTOR_PARAMS, INDUSTRY_GROUP_PARAMS dict 재현
_data = _loadSectorData()

SECTOR_PARAMS: dict = {}
for _sVal, _p in _data.get("sectorParams", {}).items():
    _s = _byValue(Sector, _sVal, Sector.UNKNOWN)
    SECTOR_PARAMS[_s] = SectorParams(
        discountRate=_p["discountRate"],
        growthRate=_p["growthRate"],
        perMultiple=_p["perMultiple"],
        pbrMultiple=_p["pbrMultiple"],
        evEbitdaMultiple=_p["evEbitdaMultiple"],
        beta=_p["beta"],
        exitMultiple=_p["exitMultiple"],
        label=_p.get("label", ""),
    )

INDUSTRY_GROUP_PARAMS: dict = {}
for _igVal, _p in _data.get("industryGroupParams", {}).items():
    _ig = _byValue(IndustryGroup, _igVal, IndustryGroup.UNKNOWN)
    INDUSTRY_GROUP_PARAMS[_ig] = SectorParams(
        discountRate=_p["discountRate"],
        growthRate=_p["growthRate"],
        perMultiple=_p["perMultiple"],
        pbrMultiple=_p["pbrMultiple"],
        evEbitdaMultiple=_p["evEbitdaMultiple"],
        beta=_p["beta"],
        exitMultiple=_p["exitMultiple"],
        label=_p.get("label", ""),
    )

__all__ = [
    "getParams",
    "getMarketParams",
    "SECTOR_PARAMS",
    "INDUSTRY_GROUP_PARAMS",
]
