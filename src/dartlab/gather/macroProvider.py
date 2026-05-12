"""DefaultMacroProvider — F3 Protocol DIP 의 macro 측 구현체.

macro 엔진이 직접 gather 를 import 하지 않도록 추상화.
"""

from __future__ import annotations

from typing import Any

import polars as pl


class DefaultMacroProvider:
    """MacroDataProvider 기본 구현 — gather/entry + macro/seriesFetch 우회."""

    def getDefaultGather(self) -> Any:
        """현재 기본 GatherEntry 인스턴스."""
        from dartlab.gather.entry import GatherEntry

        return GatherEntry()

    def applyAsOf(self, dataFrame: pl.DataFrame, asOf: str) -> pl.DataFrame:
        """as-of 필터링 — date <= asOf 행만 유지."""
        if "date" not in dataFrame.columns:
            return dataFrame
        return dataFrame.filter(pl.col("date") <= asOf)

    def fetchSeriesLatest(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 최신 값.

        Parameters
        ----------
        limit : int | None
            단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.
        """
        del limit
        from dartlab.macro.seriesFetch import fetchLatest, getGather

        try:
            return fetchLatest(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchSeriesYoy(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 YoY 변화율.

        Parameters
        ----------
        limit : int | None
            단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.
        """
        del limit
        from dartlab.macro.seriesFetch import fetchYoy, getGather

        try:
            return fetchYoy(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None
