"""DefaultMacroProvider — F3 Protocol DIP 의 macro 측 구현체.

macro 엔진이 직접 gather 를 import 하지 않도록 추상화.
"""

from __future__ import annotations

from typing import Any

import polars as pl


class DefaultMacroProvider:
    """MacroDataProvider 기본 구현 — gather/entry + macro/seriesFetch 우회."""

    def getDefaultGather(self) -> Any:
        """현재 기본 GatherEntry 인스턴스.

        Returns:
            새로 생성된 GatherEntry 인스턴스 — caller 가 macro 시리즈 fetch 에 사용.

        Raises:
            ImportError: gather.entry import 실패.

        Example:
            >>> p = DefaultMacroProvider()
            >>> g = p.getDefaultGather()
        """
        from dartlab.gather.entry import GatherEntry

        return GatherEntry()

    def applyAsOf(self, dataFrame: pl.DataFrame, asOf: str) -> pl.DataFrame:
        """as-of 필터링 — ``date <= asOf`` 행만 유지.

        Args:
            dataFrame: 입력 DataFrame.
            asOf: 컷오프 날짜 (ISO 형식).

        Returns:
            ``date`` 컬럼이 있으면 필터링한 새 DataFrame, 없으면 원본 그대로.

        Raises:
            없음 — ``date`` 컬럼 부재면 silent 반환.

        Example:
            >>> p = DefaultMacroProvider()
            >>> p.applyAsOf(df, "2024-12-31")
        """
        if "date" not in dataFrame.columns:
            return dataFrame
        return dataFrame.filter(pl.col("date") <= asOf)

    def fetchSeriesLatest(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 최신 값.

        Args:
            seriesId: macro 시리즈 ID (예: "GDP").
            limit: 단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.

        Returns:
            최신 관측치 (float). fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> p = DefaultMacroProvider()
            >>> latest = p.fetchSeriesLatest("GDP")
        """
        del limit
        from dartlab.macro.seriesFetch import fetchLatest, getGather

        try:
            return fetchLatest(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchSeriesYoy(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 YoY 변화율.

        Args:
            seriesId: macro 시리즈 ID (예: "CPI").
            limit: 단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.

        Returns:
            전년 동기 대비 변화율 (%, float). fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Example:
            >>> p = DefaultMacroProvider()
            >>> yoy = p.fetchSeriesYoy("CPI")
        """
        del limit
        from dartlab.macro.seriesFetch import fetchYoy, getGather

        try:
            return fetchYoy(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None
