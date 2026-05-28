"""ECB facade — Ecb 클래스. SdmxClient (infra) 위임 + ECB catalog 결합.

`__init__.py` thin facade 룰 — 클래스 정의 분리.
"""

from __future__ import annotations

import polars as pl

from ..infra.sdmxClient import SdmxClient, SdmxClientError
from ..infra.sdmxTypes import SdmxCatalogEntry, SdmxSeriesNotFoundError
from . import catalog as _catalog


class Ecb:
    """ECB Data Portal facade — Eurozone 거시지표.

    Args:
        client: 재사용 SdmxClient. None 이면 자체 생성.

    Example::

        e = Ecb()
        m3 = e.series("ECB_M3", startPeriod="2020-01")
        cat = e.catalog()
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
        """단일 ECB 시계열 → DataFrame ``(date, value, provider, dataflow, key)``.

        Sig: ``series(indicatorId, *, startPeriod=None, endPeriod=None) -> pl.DataFrame``

        Capabilities: catalog lookup + SdmxClient.fetch 위임 + DataFrame 반환.
        AIContext: macro engine 의 EU 거시 진입 — gather.macro(seriesId, market="EU") 와 짝.
        Guide: indicatorId 는 ``ECB_`` prefix. catalog 미등록 시 SdmxSeriesNotFoundError.
        When: 사용자가 유로존 단일 매크로 시계열 분석.
        How: catalog.getEntry → SdmxClient.fetch(ECB, dataflow, key, ...).

        Args:
            indicatorId: catalog ID (예: ``"ECB_M3"``).
            startPeriod: 시작 (예: ``"2020-01"``). None 이면 전 기간.
            endPeriod: 종료. None 이면 최신.

        Returns:
            DataFrame (date/value/provider/dataflow/key).

        Raises:
            SdmxSeriesNotFoundError: catalog 에 없는 ID.
            SdmxClientError: SDMX HTTP/JSON 실패.

        Example:
            >>> Ecb().series("ECB_M3", startPeriod="2020-01")

        See Also:
            ``catalog`` · ``compare``.
        """
        if not _catalog.hasIndicator(indicatorId):
            raise SdmxSeriesNotFoundError(f"ECB catalog 미등록: '{indicatorId}'. catalog() 호출로 가용 ID 확인.")
        entry = _catalog.getEntry(indicatorId)
        return self._client.fetch(
            "ECB",
            entry.dataflow,
            entry.key,
            startPeriod=startPeriod,
            endPeriod=endPeriod,
        )

    def compare(
        self,
        indicatorIds: list[str],
        *,
        startPeriod: str | None = None,
        endPeriod: str | None = None,
    ) -> pl.DataFrame:
        """복수 ECB 시계열 → wide DataFrame (date + indicator 컬럼 N 개).

        Sig: ``compare(indicatorIds, *, startPeriod, endPeriod) -> pl.DataFrame``

        Capabilities: indicatorIds 각각 series() 호출 + date join → wide.
        AIContext: 여러 EU 지표 동시 비교 (예: HICP vs MRO rate).
        Guide: 미등록 ID 1 개라도 있으면 SdmxSeriesNotFoundError. 개별 series 실패는 raise.
        When: ECB 복수 지표 cross-section 분석.
        How: 각 id 마다 series() → date 기준 join (outer).

        Args:
            indicatorIds: catalog ID 리스트.
            startPeriod: 시작.
            endPeriod: 종료.

        Returns:
            wide DataFrame — ``date`` + indicatorId 별 ``value`` 컬럼.

        Raises:
            SdmxSeriesNotFoundError · SdmxClientError.

        Example:
            >>> Ecb().compare(["ECB_HICP", "ECB_MRO_RATE"])

        See Also:
            ``series``.
        """
        if not indicatorIds:
            return pl.DataFrame()
        out: pl.DataFrame | None = None
        for ind_id in indicatorIds:
            df = self.series(ind_id, startPeriod=startPeriod, endPeriod=endPeriod)
            df = df.select(["date", pl.col("value").alias(ind_id)])
            out = df if out is None else out.join(df, on="date", how="full", coalesce=True)
        return out.sort("date") if out is not None else pl.DataFrame()

    def catalog(self) -> list[SdmxCatalogEntry]:
        """모든 ECB 지표 entry 리스트."""
        return _catalog.listCatalog()

    def close(self) -> None:
        """자체 생성한 client 만 종료 (재사용 client 는 caller 책임)."""
        if self._owns_client:
            self._client.close()
