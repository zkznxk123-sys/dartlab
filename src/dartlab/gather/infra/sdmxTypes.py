"""SDMX provider 공통 타입 — ECB/BIS/OECD/IMF 가 공유.

`infra/sdmxClient.SdmxClient` 와 동일 레이어. ECOS/FRED 의 CatalogEntry
(tableCode/itemCode) 와 별개 — SDMX 는 dataflow/key 표준.
"""

from __future__ import annotations

from dataclasses import dataclass


class SdmxError(Exception):
    """SDMX provider 공통 예외."""


class SdmxSeriesNotFoundError(SdmxError):
    """catalog 에 없는 indicator ID."""


@dataclass(frozen=True, slots=True)
class SdmxCatalogEntry:
    """SDMX provider 카탈로그 1 entry.

    Attributes:
        id: 사용자 노출 ID (예: ``"ECB_M3"``, ``"BIS_POLICY_RATE_USA"``).
        label: 표시명 (한국어 가능).
        group: 그룹 (예: ``"통화량"``, ``"금리"``, ``"실업"``).
        frequency: ``"D"``/``"M"``/``"Q"``/``"A"``.
        unit: 단위 (예: ``"%"``, ``"십억 EUR"``).
        description: 1~2 줄 설명.
        provider: ``"ECB"``/``"BIS"``/``"OECD"``/``"IMF"``.
        dataflow: SDMX dataflow ID (예: ``"BSI"``).
        key: SDMX 차원 키 (점 구분).
    """

    id: str
    label: str
    group: str
    frequency: str
    unit: str
    description: str
    provider: str
    dataflow: str
    key: str
