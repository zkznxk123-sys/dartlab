"""FRED facade — Fred 클래스 본체.

`__init__.py` thin facade 룰을 위해 클래스 정의 분리.
"""

from __future__ import annotations

import polars as pl

from . import catalog as _catalog
from . import transform as _transform
from .client import FredClient
from .series import fetchMeta, fetchMulti, fetchReleases, fetchSeries, searchSeries
from .types import CatalogEntry, SeriesMeta


class Fred:
    """FRED 경제지표 facade.

    Args:
        api_key: FRED API 키. None이면 ``FRED_API_KEY`` 환경변수 사용.

    Example::

        f = Fred()
        gdp = f.series("GDP")
        f.compare(["GDP", "UNRATE"], start="2020-01-01")
        f.correlation(["GDP", "UNRATE", "FEDFUNDS"])
    """

    def __init__(self, apiKey: str | None = None) -> None:
        self._client = FredClient(apiKey=apiKey)

    # ── 시계열 조회 ──

    def series(
        self,
        seriesId: str,
        *,
        start: str | None = None,
        end: str | None = None,
        freq: str | None = None,
        aggregation: str = "avg",
    ) -> pl.DataFrame:
        """단일 시계열 조회 → DataFrame ``(date, value)``.

        Parameters
        ----------
        series_id : str
            FRED 시리즈 ID (예: "GDP", "UNRATE", "CPIAUCSL").
        start : str | None
            시작일 (YYYY-MM-DD). None이면 전체.
        end : str | None
            종료일. None이면 최신까지.
        freq : str | None
            리샘플 주파수 (d/w/bw/m/q/sa/a). None이면 원본.
        aggregation : str
            리샘플 집계 방법 (avg/sum/eop).

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, ``value`` (Float64) — 지표값.

        Raises
        ------
        FredError
            FRED API HTTP 오류 또는 인증 실패.

        Example
        -------
        >>> f = Fred()
        >>> df = f.series("GDP", start="2020-01-01")
        """
        return fetchSeries(
            self._client,
            seriesId,
            start=start,
            end=end,
            freq=freq,
            aggregation=aggregation,
        )

    def search(self, query: str, *, limit: int = 20) -> pl.DataFrame:
        """키워드 검색.

        Parameters
        ----------
        query : str
            검색어 (영문).
        limit : int
            최대 결과 수.

        Returns
        -------
        pl.DataFrame
            컬럼: ``id`` (Utf8) — 시리즈 ID, ``title`` (Utf8) — 제목,
            ``frequency`` (Utf8) — 주기, ``units`` (Utf8) — 단위,
            ``popularity`` (Int64) — 인기도.

        Raises
        ------
        FredError
            FRED API HTTP 오류.

        Example
        -------
        >>> f = Fred()
        >>> hits = f.search("unemployment", limit=10)
        """
        return searchSeries(self._client, query, limit=limit)

    def meta(self, seriesId: str) -> SeriesMeta:
        """시계열 메타데이터.

        Parameters
        ----------
        series_id : str
            FRED 시리즈 ID.

        Returns
        -------
        SeriesMeta
            id, title, frequency, units, seasonal_adjustment,
            observation_start, observation_end, last_updated, notes 포함.

        Raises
        ------
        SeriesNotFoundError
            시리즈를 찾을 수 없을 때.

        Example
        -------
        >>> f = Fred()
        >>> m = f.meta("GDP")
        """
        return fetchMeta(self._client, seriesId)

    def compare(
        self,
        seriesIds: list[str],
        *,
        start: str | None = None,
        end: str | None = None,
        freq: str | None = None,
    ) -> pl.DataFrame:
        """복수 시계열 비교 → wide DataFrame.

        Parameters
        ----------
        series_ids : list[str]
            FRED 시리즈 ID 리스트.
        start : str | None
            시작일 (YYYY-MM-DD). None이면 전체.
        end : str | None
            종료일. None이면 최신까지.
        freq : str | None
            리샘플 주파수. None이면 원본.

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, 각 시리즈 ID (Float64) — 지표값.
            주파수가 다른 시리즈는 outer join 후 forward-fill.

        Raises
        ------
        FredError
            FRED API HTTP 오류.

        Example
        -------
        >>> f = Fred()
        >>> df = f.compare(["GDP", "UNRATE"], start="2020-01-01")
        """
        return fetchMulti(
            self._client,
            seriesIds,
            start=start,
            end=end,
            freq=freq,
        )

    def releases(self, *, limit: int = 20) -> pl.DataFrame:
        """최근 데이터 릴리즈 일정.

        Parameters
        ----------
        limit : int
            최대 결과 수.

        Returns
        -------
        pl.DataFrame
            컬럼: ``id`` (Int64) — 릴리즈 ID, ``name`` (Utf8) — 릴리즈명,
            ``press_release`` (Boolean) — 보도자료 여부, ``link`` (Utf8) — URL.

        Raises
        ------
        FredError
            FRED API HTTP 오류.

        Example
        -------
        >>> f = Fred()
        >>> rs = f.releases(limit=5)
        """
        return fetchReleases(self._client, limit=limit)

    # ── 카탈로그 ──

    def group(self, name: str, *, start: str | None = None, end: str | None = None) -> pl.DataFrame:
        """카탈로그 그룹 일괄 조회.

        Parameters
        ----------
        name : str
            그룹명 (growth/inflation/rates/employment/markets/housing/money).
        start : str | None
            시작일. None이면 전체.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            컬럼: ``date`` (Date) — 관측일, 각 시리즈 ID (Float64) — 지표값.

        Raises
        ------
        ValueError
            존재하지 않는 그룹명.

        Example
        -------
        >>> f = Fred()
        >>> df = f.group("rates")
        """
        ids = _catalog.getGroupIds(name)
        if not ids:
            available = ", ".join(_catalog.getGroups())
            raise ValueError(f"그룹 '{name}'을 찾을 수 없습니다. 사용 가능: {available}")
        return fetchMulti(self._client, ids, start=start, end=end)

    def catalog(self, group: str | None = None) -> pl.DataFrame:
        """카탈로그 조회.

        Parameters
        ----------
        group : str | None
            특정 그룹만 필터. None이면 전체.

        Returns
        -------
        pl.DataFrame
            컬럼: ``id`` (Utf8) — 시리즈 ID, ``label`` (Utf8) — 한글 라벨,
            ``group`` (Utf8) — 그룹명, ``frequency`` (Utf8) — 주기,
            ``unit`` (Utf8) — 단위, ``description`` (Utf8) — 설명.

        Raises
        ------
        없음
            미존재 그룹은 빈 DataFrame.

        Example
        -------
        >>> f = Fred()
        >>> cat = f.catalog(group="rates")
        """
        return _catalog.toDataframe(group)

    # ── 변환 ──

    def yoy(self, seriesId: str, *, start: str | None = None, end: str | None = None) -> pl.DataFrame:
        """전년 동기 대비 변화율 (%).

        Parameters
        ----------
        series_id : str
            FRED 시리즈 ID.
        start : str | None
            시작일. None이면 전체.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            원본 컬럼 + ``value_yoy`` (Float64) — 전년 동기 대비 변화율 (%).

        Raises
        ------
        FredError
            series fetch 실패.

        Example
        -------
        >>> f = Fred()
        >>> df = f.yoy("CPIAUCSL")
        """
        df = self.series(seriesId, start=start, end=end)
        return _transform.yoy(df)

    def mom(self, seriesId: str, *, start: str | None = None, end: str | None = None) -> pl.DataFrame:
        """전월(전기) 대비 변화율 (%).

        Parameters
        ----------
        series_id : str
            FRED 시리즈 ID.
        start : str | None
            시작일. None이면 전체.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            원본 컬럼 + ``value_mom`` (Float64) — 전월 대비 변화율 (%).

        Raises
        ------
        FredError
            series fetch 실패.

        Example
        -------
        >>> f = Fred()
        >>> df = f.mom("CPIAUCSL")
        """
        df = self.series(seriesId, start=start, end=end)
        return _transform.mom(df)

    def movingAverage(
        self,
        seriesId: str,
        *,
        window: int = 12,
        start: str | None = None,
        end: str | None = None,
    ) -> pl.DataFrame:
        """이동평균.

        Parameters
        ----------
        series_id : str
            FRED 시리즈 ID.
        window : int
            이동평균 윈도우 크기 (기).
        start : str | None
            시작일. None이면 전체.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            원본 컬럼 + ``value_ma{window}`` (Float64) — 이동평균값.

        Raises
        ------
        FredError
            series fetch 실패.

        Example
        -------
        >>> f = Fred()
        >>> df = f.movingAverage("UNRATE", window=6)
        """
        df = self.series(seriesId, start=start, end=end)
        return _transform.movingAverage(df, window=window)

    # ── 분석 ──

    def correlation(
        self,
        seriesIds: list[str],
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> pl.DataFrame:
        """복수 시계열 간 상관행렬.

        Parameters
        ----------
        series_ids : list[str]
            FRED 시리즈 ID 리스트 (2개 이상).
        start : str | None
            시작일. None이면 전체.
        end : str | None
            종료일. None이면 최신까지.

        Returns
        -------
        pl.DataFrame
            컬럼: ``column`` (Utf8) — 시리즈명, 각 시리즈 ID (Float64) — 상관계수.
            대각 = 1.0.

        Raises
        ------
        FredError
            compare fetch 실패.

        Example
        -------
        >>> f = Fred()
        >>> corr = f.correlation(["GDP", "UNRATE", "FEDFUNDS"])
        """
        df = self.compare(seriesIds, start=start, end=end)
        return _transform.correlation(df)

    def leadLag(
        self,
        idA: str,
        idB: str,
        *,
        maxLag: int = 12,
        start: str | None = None,
        end: str | None = None,
    ) -> pl.DataFrame:
        """선행/후행 상관분석.

        Parameters
        ----------
        idA, idB : str
            FRED 시리즈 ID 쌍.
        maxLag : int
            ± lag 최대 (기). 기본 12.
        start, end : str | None
            조회 범위.

        Returns:
            DataFrame ``(lag, correlation)``. 양수 lag = id_b가 후행.

        Raises
        ------
        FredError
            compare fetch 실패.

        Example
        -------
        >>> f = Fred()
        >>> df = f.leadLag("FEDFUNDS", "UNRATE", maxLag=6)
        """
        df = self.compare([idA, idB], start=start, end=end)
        return _transform.leadLag(df, idA, idB, maxLag=maxLag)

    # ── 정리 ──

    def close(self) -> None:
        """HTTP 세션 종료.

        Returns
        -------
        None

        Raises
        ------
        없음
            세션이 이미 종료된 경우에도 graceful.

        Example
        -------
        >>> f = Fred()
        >>> f.close()
        """
        self._client.close()

    def __repr__(self) -> str:
        n = len(_catalog.getAllIds())
        return f"Fred(catalog={n} series, groups={_catalog.getGroups()})"


__all__ = ["Fred"]
