"""ECOS facade — Ecos 클래스 본체.

`__init__.py` thin facade 룰을 위해 클래스 정의 분리.
"""

from __future__ import annotations

import polars as pl

from . import catalog as _catalog
from .client import EcosClient
from .series import fetchMulti, fetchSeries
from .types import CatalogEntry


class Ecos:
    """ECOS 경제지표 facade.

    Args:
        apiKey: ECOS API 키. None이면 ``ECOS_API_KEY`` 환경변수 사용.

    Example::

        e = Ecos()
        cpi = e.series("CPI")
        e.compare(["CPI", "BASE_RATE", "USDKRW"])
    """

    def __init__(self, apiKey: str | None = None) -> None:
        self._client = EcosClient(apiKey=apiKey)

    # ── 시계열 조회 ──

    def series(
        self,
        indicatorId: str,
        *,
        start: str | None = None,
        end: str | None = None,
        enrich: bool = False,
    ) -> pl.DataFrame:
        """단일 시계열 조회 → DataFrame ``(date, value)``.

        Parameters
        ----------
        indicatorId : str
            카탈로그 지표 ID (예: "GDP", "CPI", "BASE_RATE").
        start : str | None
            시작일 (YYYY, YYYYMM, YYYYMMDD). None이면 2000년부터.
        end : str | None
            종료일. None이면 최신까지.
        enrich : bool
            True이면 변화율 추가 + Parquet 영구 캐시.

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, ``value`` (Float64) — 지표값.
            enrich=True 시 변화율 컬럼 추가.
        """
        return fetchSeries(self._client, indicatorId, start=start, end=end, enrich=enrich)

    def compare(
        self,
        indicatorIds: list[str],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> pl.DataFrame:
        """복수 시계열 비교 → wide DataFrame ``(date, CPI, BASE_RATE, ...)``.

        Parameters
        ----------
        indicatorIds : list[str]
            카탈로그 지표 ID 리스트 (예: ["CPI", "BASE_RATE", "USDKRW"]).
        start : str | None
            시작일 (YYYY, YYYYMM, YYYYMMDD). None이면 2000년부터.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, 각 지표 ID (Float64) — 지표값.
            주기가 다른 지표는 outer join 후 forward-fill.
        """
        return fetchMulti(self._client, indicatorIds, start=start, end=end)

    # ── 카탈로그 ──

    def catalog(self, group: str | None = None) -> pl.DataFrame:
        """카탈로그 조회.

        Parameters
        ----------
        group : str | None
            특정 그룹만 필터. None이면 전체.

        Returns
        -------
        pl.DataFrame
            컬럼: ``id`` (Utf8) — 지표 ID, ``label`` (Utf8) — 한글 라벨,
            ``group`` (Utf8) — 그룹명, ``frequency`` (Utf8) — 주기 코드,
            ``unit`` (Utf8) — 단위, ``description`` (Utf8) — 설명.
        """
        return _catalog.toDataframe(group)

    def search(self, keyword: str) -> list[CatalogEntry]:
        """키워드로 카탈로그 검색.

        Parameters
        ----------
        keyword : str
            검색 키워드 (ID, 라벨, 설명에서 매칭).

        Returns
        -------
        list[CatalogEntry]
            매칭된 카탈로그 엔트리 리스트. 각 엔트리에
            id, label, group, frequency, unit, description 포함.
        """
        return _catalog.search(keyword)

    def group(self, name: str, *, start: str | None = None, end: str | None = None) -> pl.DataFrame:
        """카탈로그 그룹 일괄 조회.

        Parameters
        ----------
        name : str
            그룹명 (국민계정/물가/금리/환율/통화·금융/산업·생산/무역/경기·심리/부동산/고용).
        start : str | None
            시작일. None이면 2000년부터.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, 각 지표 ID (Float64) — 지표값.
            그룹 내 모든 지표를 wide 형태로 조인.

        Raises
        ------
        ValueError
            존재하지 않는 그룹명.
        """
        ids = _catalog.getGroupIds(name)
        if not ids:
            available = ", ".join(_catalog.getGroups())
            raise ValueError(f"그룹 '{name}'을 찾을 수 없습니다. 사용 가능: {available}")
        return fetchMulti(self._client, ids, start=start, end=end)

    # ── 정리 ──

    def close(self) -> None:
        """HTTP 세션 종료.

        Returns
        -------
        None
        """
        self._client.close()

    def __repr__(self) -> str:
        n = len(_catalog.getAllIds())
        return f"Ecos(catalog={n} series, groups={_catalog.getGroups()})"


__all__ = ["Ecos"]
