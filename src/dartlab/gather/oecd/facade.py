"""OECD facade — Oecd 클래스. SdmxClient (infra) 위임 + OECD catalog 결합."""

from __future__ import annotations

import polars as pl

from ..infra.sdmxClient import SdmxClient
from ..infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError
from . import catalog as _catalog


class Oecd:
    """OECD SDMX facade — G20 거시지표.

    Args:
        client: 재사용 SdmxClient. None 이면 자체 생성.

    Example::

        o = Oecd()
        cpi = o.series("OECD_CPI_US")
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
        """단일 OECD 시계열 → DataFrame ``(date, value, provider, dataflow, key)``.

        Sig: ``series(indicatorId, *, startPeriod=None, endPeriod=None) -> pl.DataFrame``

        Capabilities: catalog lookup + SdmxClient.fetch 위임.
        AIContext: macro engine 의 G20 거시 진입 — gather.macro(seriesId, market="GLOBAL") 와 짝.
        Guide: indicatorId 는 ``OECD_`` prefix. catalog 미등록 시 SdmxSeriesNotFoundError.
        When: 사용자가 OECD G20 거시 단일 시계열 분석.
        How: catalog.getEntry → SdmxClient.fetch(OECD, dataflow, key, ...).

        Args:
            indicatorId: catalog ID (예: ``"OECD_CPI_US"``).
            startPeriod: 시작. None 이면 전 기간.
            endPeriod: 종료. None 이면 최신.

        Returns:
            DataFrame (date/value/provider/dataflow/key).

        Raises:
            SdmxSeriesNotFoundError · SdmxClientError.

        Example:
            >>> Oecd().series("OECD_CPI_US")

        See Also:
            ``catalog``.
        """
        if not _catalog.hasIndicator(indicatorId):
            raise SdmxSeriesNotFoundError(f"OECD catalog 미등록: '{indicatorId}'. catalog() 호출로 가용 ID 확인.")
        entry = _catalog.getEntry(indicatorId)
        return self._client.fetch(
            "OECD",
            entry.dataflow,
            entry.key,
            startPeriod=startPeriod,
            endPeriod=endPeriod,
        )

    def catalog(self) -> list[SdmxCatalogEntry]:
        """모든 OECD 지표 entry 리스트."""
        return _catalog.listCatalog()

    def close(self) -> None:
        """자체 생성한 client 만 종료."""
        if self._owns_client:
            self._client.close()
