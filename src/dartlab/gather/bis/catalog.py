"""BIS 지표 카탈로그 — 글로벌 통화·신용·환율 핵심 시리즈.

BIS Stats SDMX: https://stats.bis.org/api/v1
신규 지표 추가는 본 dict 에만.
"""

from __future__ import annotations

from ..infra.sdmxTypes import SdmxCatalogEntry

_INDICATORS: dict[str, SdmxCatalogEntry] = {
    "BIS_POLICY_RATE_US": SdmxCatalogEntry(
        id="BIS_POLICY_RATE_US",
        label="미국 정책금리 (Central Bank)",
        group="금리",
        frequency="M",
        unit="%",
        description="BIS Central Bank Policy Rates — US Fed funds target (월간 평균).",
        provider="BIS",
        dataflow="WS_CBPOL_D",
        key="D.US",
    ),
    "BIS_POLICY_RATE_EU": SdmxCatalogEntry(
        id="BIS_POLICY_RATE_EU",
        label="유로존 정책금리 (ECB)",
        group="금리",
        frequency="M",
        unit="%",
        description="BIS Central Bank Policy Rates — Euro area MRO.",
        provider="BIS",
        dataflow="WS_CBPOL_D",
        key="D.XM",
    ),
    "BIS_POLICY_RATE_JP": SdmxCatalogEntry(
        id="BIS_POLICY_RATE_JP",
        label="일본 정책금리 (BOJ)",
        group="금리",
        frequency="M",
        unit="%",
        description="BIS Central Bank Policy Rates — BOJ uncollateralized overnight call.",
        provider="BIS",
        dataflow="WS_CBPOL_D",
        key="D.JP",
    ),
    "BIS_POLICY_RATE_KR": SdmxCatalogEntry(
        id="BIS_POLICY_RATE_KR",
        label="한국 정책금리 (BOK)",
        group="금리",
        frequency="M",
        unit="%",
        description="BIS Central Bank Policy Rates — Bank of Korea base rate.",
        provider="BIS",
        dataflow="WS_CBPOL_D",
        key="D.KR",
    ),
    "BIS_CREDIT_GAP_US": SdmxCatalogEntry(
        id="BIS_CREDIT_GAP_US",
        label="미국 신용갭 (Credit-to-GDP gap)",
        group="신용",
        frequency="Q",
        unit="%p",
        description="Total credit to private non-financial sector — gap from trend.",
        provider="BIS",
        dataflow="WS_CREDIT_GAP",
        key="Q.US.A",
    ),
    "BIS_DEBT_HH_US": SdmxCatalogEntry(
        id="BIS_DEBT_HH_US",
        label="미국 가계부채 (GDP 대비)",
        group="신용",
        frequency="Q",
        unit="% of GDP",
        description="Credit to households as a % of GDP — US.",
        provider="BIS",
        dataflow="WS_TC",
        key="Q.US.H.A.M.770.A",
    ),
    "BIS_EER_BROAD_USD": SdmxCatalogEntry(
        id="BIS_EER_BROAD_USD",
        label="미국 실효환율 (Broad)",
        group="환율",
        frequency="M",
        unit="index 2010=100",
        description="BIS Broad Effective Exchange Rate — USD.",
        provider="BIS",
        dataflow="WS_EER_M",
        key="M.B.US",
    ),
    "BIS_EER_NARROW_USD": SdmxCatalogEntry(
        id="BIS_EER_NARROW_USD",
        label="미국 실효환율 (Narrow)",
        group="환율",
        frequency="M",
        unit="index 2010=100",
        description="BIS Narrow Effective Exchange Rate — USD.",
        provider="BIS",
        dataflow="WS_EER_M",
        key="M.N.US",
    ),
}


def listCatalog() -> list[SdmxCatalogEntry]:
    """모든 BIS 지표 entry 리스트."""
    return list(_INDICATORS.values())


def getEntry(indicatorId: str) -> SdmxCatalogEntry:
    """indicator ID → SdmxCatalogEntry. KeyError on 미등록."""
    if indicatorId not in _INDICATORS:
        raise KeyError(f"BIS catalog 미등록: '{indicatorId}'. 가용: {sorted(_INDICATORS)}")
    return _INDICATORS[indicatorId]


def hasIndicator(indicatorId: str) -> bool:
    """indicator ID 가 BIS catalog 에 있는지."""
    return indicatorId in _INDICATORS
