"""ECB 지표 카탈로그 — Eurozone 핵심 거시 8 시리즈.

신규 지표 추가는 본 dict 에만. SDMX dataflow/key 는 ECB Data Portal:
https://data.ecb.europa.eu/help/api/data
"""

from __future__ import annotations

from ..infra.sdmxTypes import SdmxCatalogEntry

# id 컨벤션 — ``ECB_`` prefix 로 macro 라우팅 시 자동 감지.
_INDICATORS: dict[str, SdmxCatalogEntry] = {
    "ECB_M3": SdmxCatalogEntry(
        id="ECB_M3",
        label="유로존 M3 통화량",
        group="통화량",
        frequency="M",
        unit="십억 EUR",
        description="Monetary aggregate M3 — 유로존 광의 통화 (계절조정 outstanding).",
        provider="ECB",
        dataflow="BSI",
        key="M.U2.Y.V.M30.X.1.U2.2300.Z01.E",
    ),
    "ECB_HICP": SdmxCatalogEntry(
        id="ECB_HICP",
        label="유로존 HICP (소비자물가)",
        group="물가",
        frequency="M",
        unit="% YoY",
        description="Harmonised Index of Consumer Prices — 유로존 전 품목 전년동월대비.",
        provider="ECB",
        dataflow="ICP",
        key="M.U2.N.000000.4.ANR",
    ),
    "ECB_DEPO_RATE": SdmxCatalogEntry(
        id="ECB_DEPO_RATE",
        label="ECB 예금금리 (DFR)",
        group="금리",
        frequency="D",
        unit="%",
        description="Deposit Facility Rate — ECB 은행 익일물 예치 금리.",
        provider="ECB",
        dataflow="FM",
        key="B.U2.EUR.4F.KR.DFR.LEV",
    ),
    "ECB_MRO_RATE": SdmxCatalogEntry(
        id="ECB_MRO_RATE",
        label="ECB 정책금리 (MRO)",
        group="금리",
        frequency="D",
        unit="%",
        description="Main Refinancing Operations rate — ECB 핵심 정책 금리.",
        provider="ECB",
        dataflow="FM",
        key="B.U2.EUR.4F.KR.MRR_FR.LEV",
    ),
    "ECB_UNEMP": SdmxCatalogEntry(
        id="ECB_UNEMP",
        label="유로존 실업률",
        group="고용",
        frequency="M",
        unit="%",
        description="Unemployment rate — 유로존 15-74 세 (계절조정).",
        provider="ECB",
        dataflow="LFSI",
        key="M.I9.S.UNEHRT.TOTAL0.15_74.T",
    ),
    "ECB_EURUSD": SdmxCatalogEntry(
        id="ECB_EURUSD",
        label="EUR/USD 환율",
        group="환율",
        frequency="D",
        unit="USD per EUR",
        description="ECB 일일 기준 환율 (USD 대비).",
        provider="ECB",
        dataflow="EXR",
        key="D.USD.EUR.SP00.A",
    ),
    "ECB_BUND_10Y": SdmxCatalogEntry(
        id="ECB_BUND_10Y",
        label="독일 10년 국채금리",
        group="금리",
        frequency="D",
        unit="%",
        description="German 10-year government bond yield (benchmark).",
        provider="ECB",
        dataflow="FM",
        key="D.DE.EUR.4F.BB.U_A_10Y.YLD",
    ),
    "ECB_GDP_EA": SdmxCatalogEntry(
        id="ECB_GDP_EA",
        label="유로존 GDP",
        group="국민계정",
        frequency="Q",
        unit="십억 EUR (chain-linked)",
        description="Euro area GDP — chain-linked volume, 계절·달력 조정.",
        provider="ECB",
        dataflow="MNA",
        key="Q.Y.I9.W2.S1.S1.B.B1GQ._Z._Z._Z.EUR.LR.GY",
    ),
}


def listCatalog() -> list[SdmxCatalogEntry]:
    """모든 ECB 지표 entry 리스트."""
    return list(_INDICATORS.values())


def getEntry(indicatorId: str) -> SdmxCatalogEntry:
    """indicator ID → SdmxCatalogEntry.

    Raises:
        KeyError: 미등록 ID.
    """
    if indicatorId not in _INDICATORS:
        raise KeyError(f"ECB catalog 미등록: '{indicatorId}'. 가용: {sorted(_INDICATORS)}")
    return _INDICATORS[indicatorId]


def hasIndicator(indicatorId: str) -> bool:
    """indicator ID 가 ECB catalog 에 있는지."""
    return indicatorId in _INDICATORS
