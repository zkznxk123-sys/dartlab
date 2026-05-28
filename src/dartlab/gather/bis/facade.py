"""BIS facade — Bis 클래스. SdmxClient (infra) 위임 + BIS catalog 결합."""

from __future__ import annotations

import polars as pl

from ..infra.sdmxClient import SdmxClient
from ..infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError
from . import catalog as _catalog


class Bis:
    """BIS Statistics facade — 글로벌 통화·신용·환율.

    Args:
        client: 재사용 SdmxClient. None 이면 자체 생성.

    Example::

        b = Bis()
        rate = b.series("BIS_POLICY_RATE_US")
    """

    def __init__(self, client: SdmxClient | None = None) -> None:
        self._client = client or SdmxClient()
        self._owns_client = client is None

    def series(
        self,
        indicatorId: str,
        *,
        startPeriod: str | None = None,
        endPeriod: str | None = None,
    ) -> pl.DataFrame:
        """단일 BIS 시계열 → DataFrame ``(date, value, provider, dataflow, key)``.

        Sig: ``series(indicatorId, *, startPeriod=None, endPeriod=None) -> pl.DataFrame``

        Capabilities: catalog lookup + SdmxClient.fetch 위임.
        AIContext: macro engine 의 글로벌 통화·신용 진입 — gather.macro(seriesId, market="GLOBAL") 와 짝.
        Guide: indicatorId 는 ``BIS_`` prefix. catalog 미등록 시 SdmxSeriesNotFoundError.
        When: 사용자가 BIS 단일 글로벌 매크로 분석.
        How: catalog.getEntry → SdmxClient.fetch(BIS, dataflow, key, ...).

        Args:
            indicatorId: catalog ID (예: ``"BIS_POLICY_RATE_US"``).
            startPeriod: 시작. None 이면 전 기간.
            endPeriod: 종료. None 이면 최신.

        Returns:
            DataFrame (date/value/provider/dataflow/key).

        Raises:
            SdmxSeriesNotFoundError · SdmxClientError.

        Example:
            >>> Bis().series("BIS_POLICY_RATE_US")

        See Also:
            ``catalog``.
        """
        if not _catalog.hasIndicator(indicatorId):
            raise SdmxSeriesNotFoundError(f"BIS catalog 미등록: '{indicatorId}'. catalog() 호출로 가용 ID 확인.")
        entry = _catalog.getEntry(indicatorId)
        return self._client.fetch(
            "BIS",
            entry.dataflow,
            entry.key,
            startPeriod=startPeriod,
            endPeriod=endPeriod,
        )

    def catalog(self) -> list[SdmxCatalogEntry]:
        """모든 BIS 지표 entry 리스트."""
        return _catalog.listCatalog()

    def close(self) -> None:
        """자체 생성한 client 만 종료."""
        if self._owns_client:
            self._client.close()
