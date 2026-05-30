"""OECD 지표 카탈로그 — G20 거시지표 핵심 시리즈.

OECD SDMX: https://sdmx.oecd.org/public/rest (구 endpoint 2024 deprecated)
"""

from __future__ import annotations

from ..infra.sdmxTypes import SdmxCatalogEntry

_INDICATORS: dict[str, SdmxCatalogEntry] = {
    "OECD_GDP_US": SdmxCatalogEntry(
        id="OECD_GDP_US",
        label="미국 GDP 성장률 (전년동기대비)",
        group="국민계정",
        frequency="Q",
        unit="% YoY",
        description="OECD National Accounts — US Real GDP growth (yoy).",
        provider="OECD",
        dataflow="OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA",
        key="Q.USA.S1..B1GQ......GY.",
    ),
    "OECD_GDP_KR": SdmxCatalogEntry(
        id="OECD_GDP_KR",
        label="한국 GDP 성장률",
        group="국민계정",
        frequency="Q",
        unit="% YoY",
        description="OECD National Accounts — Korea Real GDP growth.",
        provider="OECD",
        dataflow="OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA",
        key="Q.KOR.S1..B1GQ......GY.",
    ),
    "OECD_CPI_US": SdmxCatalogEntry(
        id="OECD_CPI_US",
        label="미국 CPI (전년동월대비)",
        group="물가",
        frequency="M",
        unit="% YoY",
        description="OECD Prices — US CPI all items (yoy).",
        provider="OECD",
        dataflow="OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL",
        key="USA.M.N.CPI.PA._T.N.GY",
    ),
    "OECD_CPI_OECD": SdmxCatalogEntry(
        id="OECD_CPI_OECD",
        label="OECD 평균 CPI",
        group="물가",
        frequency="M",
        unit="% YoY",
        description="OECD-Total CPI all items (yoy).",
        provider="OECD",
        dataflow="OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL",
        key="OECD.M.N.CPI.PA._T.N.GY",
    ),
    "OECD_UNEMP_US": SdmxCatalogEntry(
        id="OECD_UNEMP_US",
        label="미국 실업률",
        group="고용",
        frequency="M",
        unit="%",
        description="OECD Labor — US harmonised unemployment rate.",
        provider="OECD",
        dataflow="OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M",
        key="USA.M..._T.Y_GE15..",
    ),
    "OECD_LEI": SdmxCatalogEntry(
        id="OECD_LEI",
        label="OECD 선행지수 (Composite Leading Indicator)",
        group="선행지표",
        frequency="M",
        unit="index 100=trend",
        description="Composite Leading Indicator — OECD area, amplitude adjusted.",
        provider="OECD",
        dataflow="OECD.SDD.STES,DSD_STES@DF_CLI",
        key="OECD.M.LI.AA.G1.IX..",
    ),
    "OECD_BCI": SdmxCatalogEntry(
        id="OECD_BCI",
        label="OECD 기업 신뢰지수 (BCI)",
        group="신뢰지수",
        frequency="M",
        unit="index 100=neutral",
        description="Business Confidence Indicator — OECD area.",
        provider="OECD",
        dataflow="OECD.SDD.STES,DSD_STES@DF_BCICP",
        key="OECD.M.BC.AA.G1.IX..",
    ),
    "OECD_CCI": SdmxCatalogEntry(
        id="OECD_CCI",
        label="OECD 소비자 신뢰지수 (CCI)",
        group="신뢰지수",
        frequency="M",
        unit="index 100=neutral",
        description="Consumer Confidence Indicator — OECD area.",
        provider="OECD",
        dataflow="OECD.SDD.STES,DSD_STES@DF_BCICP",
        key="OECD.M.CC.AA.G1.IX..",
    ),
}


def listCatalog(*, limit: int | None = None) -> list[SdmxCatalogEntry]:
    """모든 OECD 지표 entry 리스트 반환.

    Args:
        limit: 반환 entry 최대 개수. None=전체(8).

    Returns:
        SdmxCatalogEntry list. limit 지정 시 앞에서 limit 개.

    Example:
        >>> len(listCatalog(limit=3))
        3

    Raises:
        없음.
    """
    entries = list(_INDICATORS.values())
    return entries[:limit] if limit is not None else entries


def getEntry(indicatorId: str) -> SdmxCatalogEntry:
    """indicator ID → SdmxCatalogEntry 조회. 미등록 시 KeyError."""
    if indicatorId not in _INDICATORS:
        raise KeyError(f"OECD catalog 미등록: '{indicatorId}'. 가용: {sorted(_INDICATORS)}")
    return _INDICATORS[indicatorId]


def hasIndicator(indicatorId: str) -> bool:
    """indicator ID 가 OECD catalog 에 등록되어 있는지 여부."""
    return indicatorId in _INDICATORS
