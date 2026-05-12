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

        Capabilities: MacroDataProvider Protocol — GatherEntry lazy import + 인스턴스화.
        AIContext: macro engine 이 gather 본체 직접 의존 회피 — F3 Protocol DIP 의 macro 측 본체.
        Guide: 매 호출마다 new GatherEntry — singleton 아님 (cache 공유는 entry 안 Gather singleton).
        When: macro engine 이 시리즈 fetch 위해 gather entry 필요 시.
        How: lazy ``from dartlab.gather.entry import GatherEntry`` → 인스턴스 반환.

        Returns:
            새로 생성된 GatherEntry 인스턴스 — caller 가 macro 시리즈 fetch 에 사용.

        Raises:
            ImportError: gather.entry import 실패.

        Requires:
            ``dartlab.gather.entry`` import 가능.

        Example:
            >>> p = DefaultMacroProvider()
            >>> g = p.getDefaultGather()

        See Also:
            entry.GatherEntry : 위임 대상.
            core.macroProvider.MacroDataProvider : 본 메서드의 Protocol 정의.
        """
        from dartlab.gather.entry import GatherEntry

        return GatherEntry()

    def applyAsOf(self, dataFrame: pl.DataFrame, asOf: str) -> pl.DataFrame:
        """as-of 필터링 — ``date <= asOf`` 행만 유지.

        Capabilities: ``date`` 컬럼 cutoff 필터 — look-ahead bias 차단.
        AIContext: macro 회귀 분석 시 분석 시점 이후 데이터 누출 방지.
        Guide: ISO 형식 (YYYY-MM-DD) 권장. date 컬럼 없으면 원본 통과.
        When: 백테스트 / pseudo-prophet 분석 시.
        How: ``df.filter(pl.col('date') <= asOf)``.

        Args:
            dataFrame: 입력 DataFrame.
            asOf: 컷오프 날짜 (ISO 형식).

        Returns:
            ``date`` 컬럼이 있으면 필터링한 새 DataFrame, 없으면 원본 그대로.

        Raises:
            없음 — ``date`` 컬럼 부재면 silent 반환.

        Requires:
            dataFrame 의 ``date`` 컬럼 (있을 때만 적용).

        Example:
            >>> p = DefaultMacroProvider()
            >>> p.applyAsOf(df, "2024-12-31")

        See Also:
            fetchSeriesLatest · fetchSeriesYoy : asOf 미적용 단건 fetch.
        """
        if "date" not in dataFrame.columns:
            return dataFrame
        return dataFrame.filter(pl.col("date") <= asOf)

    def fetchSeriesLatest(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 최신 값.

        Capabilities: macro.seriesFetch.fetchLatest 위임 + 예외 흡수 → None fail-soft.
        AIContext: 단건 매크로 값 표시 (UI tile, narrative 단순 인용).
        Guide: 실패 시 None — caller 가 None check.
        When: 단일 시점 매크로 값 표시 / KPI 대시보드 / narrative 인용 시.
        How: ``getGather(None)`` + ``fetchLatest(g, seriesId)`` try/except → None.

        Args:
            seriesId: macro 시리즈 ID (예: "GDP").
            limit: 단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.

        Returns:
            최신 관측치 (float). fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Requires:
            ``dartlab.macro.seriesFetch`` import 가능.

        Example:
            >>> p = DefaultMacroProvider()
            >>> latest = p.fetchSeriesLatest("GDP")

        See Also:
            fetchSeriesYoy : 동행 YoY 단건.
            applyAsOf : 시계열 cutoff.
        """
        del limit
        from dartlab.macro.seriesFetch import fetchLatest, getGather

        try:
            return fetchLatest(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None

    def fetchSeriesYoy(self, seriesId: str, *, limit: int | None = None) -> float | None:
        """seriesId 의 YoY 변화율.

        Capabilities: macro.seriesFetch.fetchYoy 위임 + 예외 흡수.
        AIContext: 인플레이션/생산 YoY 비교 분석 진입 (CPI/IPI/PPI 등).
        Guide: 단건 float — 시계열 필요 시 macro entry.
        When: 단일 YoY 값 표시 / regime classifier 입력 시.
        How: ``getGather(None)`` + ``fetchYoy(g, seriesId)`` try/except → None.

        Args:
            seriesId: macro 시리즈 ID (예: "CPI").
            limit: 단건 float 반환 함수라 무시된다. 인터페이스 호환 목적.

        Returns:
            전년 동기 대비 변화율 (%, float). fetch 실패 시 None.

        Raises:
            없음 — ValueError/RuntimeError/KeyError 는 내부에서 흡수.

        Requires:
            ``dartlab.macro.seriesFetch`` import 가능.

        Example:
            >>> p = DefaultMacroProvider()
            >>> yoy = p.fetchSeriesYoy("CPI")

        See Also:
            fetchSeriesLatest : 동행 단건 latest.
        """
        del limit
        from dartlab.macro.seriesFetch import fetchYoy, getGather

        try:
            return fetchYoy(getGather(None), seriesId)
        except (ValueError, RuntimeError, KeyError):
            return None
