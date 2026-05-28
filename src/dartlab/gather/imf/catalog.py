"""IMF 지표 카탈로그 — IFS/BOP/WEO 핵심 글로벌 시리즈.

IMF SDMX Central: https://sdmxcentral.imf.org/ws/public/sdmxapi/rest
"""

from __future__ import annotations

from ..infra.sdmxTypes import SdmxCatalogEntry

_INDICATORS: dict[str, SdmxCatalogEntry] = {
    "IMF_GDP_US": SdmxCatalogEntry(
        id="IMF_GDP_US",
        label="미국 GDP (명목, USD)",
        group="국민계정",
        frequency="A",
        unit="십억 USD",
        description="IMF IFS — US GDP at current prices.",
        provider="IMF",
        dataflow="IFS",
        key="A.US.NGDP_XDC",
    ),
    "IMF_GDP_WORLD": SdmxCatalogEntry(
        id="IMF_GDP_WORLD",
        label="세계 GDP (PPP)",
        group="국민계정",
        frequency="A",
        unit="십억 USD PPP",
        description="IMF WEO — World GDP at PPP.",
        provider="IMF",
        dataflow="WEO",
        key="A.W00.NGDP_RPCH",
    ),
    "IMF_CPI_US": SdmxCatalogEntry(
        id="IMF_CPI_US",
        label="미국 CPI (IFS)",
        group="물가",
        frequency="M",
        unit="index 2010=100",
        description="IMF IFS — US Consumer Price Index, all items.",
        provider="IMF",
        dataflow="IFS",
        key="M.US.PCPI_IX",
    ),
    "IMF_FX_USD_KRW": SdmxCatalogEntry(
        id="IMF_FX_USD_KRW",
        label="환율 KRW/USD",
        group="환율",
        frequency="M",
        unit="KRW per USD",
        description="IMF IFS — KRW per USD period average.",
        provider="IMF",
        dataflow="IFS",
        key="M.KR.ENDA_XDC_USD_RATE",
    ),
    "IMF_FX_USD_JPY": SdmxCatalogEntry(
        id="IMF_FX_USD_JPY",
        label="환율 JPY/USD",
        group="환율",
        frequency="M",
        unit="JPY per USD",
        description="IMF IFS — JPY per USD period average.",
        provider="IMF",
        dataflow="IFS",
        key="M.JP.ENDA_XDC_USD_RATE",
    ),
    "IMF_RES_KR": SdmxCatalogEntry(
        id="IMF_RES_KR",
        label="한국 외환보유고",
        group="국제수지",
        frequency="M",
        unit="백만 USD",
        description="IMF IFS — Korea total reserves excluding gold.",
        provider="IMF",
        dataflow="IFS",
        key="M.KR.RAXG_USD",
    ),
    "IMF_BOP_CA_KR": SdmxCatalogEntry(
        id="IMF_BOP_CA_KR",
        label="한국 경상수지",
        group="국제수지",
        frequency="Q",
        unit="백만 USD",
        description="IMF BOP — Korea current account balance.",
        provider="IMF",
        dataflow="BOP",
        key="Q.KR.BCA_BP6_USD",
    ),
    "IMF_OIL_BRENT": SdmxCatalogEntry(
        id="IMF_OIL_BRENT",
        label="Brent 원유 가격",
        group="원자재",
        frequency="M",
        unit="USD per barrel",
        description="IMF PCPS — Brent crude oil spot price.",
        provider="IMF",
        dataflow="PCPS",
        key="M.W00.POILBRE.USD",
    ),
}


def listCatalog() -> list[SdmxCatalogEntry]:
    """모든 IMF 지표 entry 리스트 반환."""
    return list(_INDICATORS.values())


def getEntry(indicatorId: str) -> SdmxCatalogEntry:
    """indicator ID → SdmxCatalogEntry 조회. 미등록 시 KeyError."""
    if indicatorId not in _INDICATORS:
        raise KeyError(f"IMF catalog 미등록: '{indicatorId}'. 가용: {sorted(_INDICATORS)}")
    return _INDICATORS[indicatorId]


def hasIndicator(indicatorId: str) -> bool:
    """indicator ID 가 IMF catalog 에 등록되어 있는지."""
    return indicatorId in _INDICATORS
