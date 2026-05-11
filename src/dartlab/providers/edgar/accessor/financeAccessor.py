"""EDGAR finance namespace — XBRL 정규화 재무 데이터."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import polars as pl

from dartlab.core.memory import _CACHE_MISSING

if TYPE_CHECKING:
    from dartlab.providers.edgar.company import Company


class _FinanceAccessor:
    """EDGAR finance namespace. XBRL 정규화 재무 데이터."""

    def __init__(self, company: Company):
        self._company = company

    def _stmtDf(self, stmtKey: str, *, freq: str = "Q") -> pl.DataFrame | None:
        """재무제표 DataFrame. freq="Q"(분기, 기본) 또는 "Y"(연간)."""
        cacheKey = f"_finance_{stmtKey}_{freq}"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]

        result = self._company._buildFinanceSeries(freq=freq)
        if result is None:
            self._company._cache[cacheKey] = None
            return None

        series, years = result
        stmtData = series.get(stmtKey)
        if not stmtData:
            self._company._cache[cacheKey] = None
            return None

        from dartlab.core.utils.labels import getKoreanLabels
        from dartlab.providers.edgar.finance.mapper import EdgarMapper

        krLabels = getKoreanLabels()
        lineOrder = EdgarMapper.getLineOrder()  # snakeId → line 번호

        # standardAccounts line 순서로 정렬 (매핑 없으면 맨 뒤)
        sortedItems = sorted(stmtData.items(), key=lambda kv: lineOrder.get(kv[0], 9999))
        rows = []
        for snakeId, values in sortedItems:
            label = krLabels.get(snakeId, snakeId)  # 한국어 매핑 없으면 snakeId 그대로
            # 컬럼명 표준: "항목" (sections 사상)
            row: dict[str, Any] = {
                "snakeId": snakeId,
                "항목": label,
            }
            for i, year in enumerate(years):
                row[str(year)] = values[i] if i < len(values) else None
            rows.append(row)

        if not rows:
            self._company._cache[cacheKey] = None
            return None

        result = pl.DataFrame(rows)
        # 기간 컬럼: "2025-Q4" → "2025Q4" (DART 형식 통일) + 역순 정렬
        periodCols = [c for c in result.columns if c not in ("snakeId", "항목")]
        renameMap = {c: c.replace("-", "") for c in periodCols if "-" in c}
        if renameMap:
            result = result.rename(renameMap)
            periodCols = [renameMap.get(c, c) for c in periodCols]
        # 전부 null인 빈 컬럼 제거
        nonEmpty = [c for c in periodCols if result[c].null_count() < result.height]
        result = result.select(["snakeId", "항목"] + nonEmpty[::-1])
        self._company._cache[cacheKey] = result
        return result

    @property
    def BS(self) -> pl.DataFrame | None:
        """BS — TODO 한국어 동작 설명."""
        return self._stmtDf("BS")

    @property
    def IS(self) -> pl.DataFrame | None:
        """IS — TODO 한국어 동작 설명."""
        return self._stmtDf("IS")

    @property
    def CF(self) -> pl.DataFrame | None:
        """CF — TODO 한국어 동작 설명."""
        return self._stmtDf("CF")

    @property
    def CIS(self) -> pl.DataFrame | None:
        """CIS — TODO 한국어 동작 설명."""
        return self._stmtDf("CI")

    @property
    def ratios(self):
        """ratios — TODO 한국어 동작 설명."""
        val = self._company._cache.get("_ratios", _CACHE_MISSING)
        if val is _CACHE_MISSING:
            from dartlab.analysis.financial.ratios import calcRatios

            annual = self._company._buildFinanceSeries(freq="Y")
            if annual is None:
                val = None
            else:
                aSeries, _ = annual
                val = calcRatios(aSeries, annual=True)
            self._company._cache["_ratios"] = val
        return val

    @property
    def ratioSeries(self):
        """ratioSeries — TODO 한국어 동작 설명."""
        cacheKey = "_ratioSeries"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]
        annual = self._company._buildFinanceSeries(freq="Y")
        if annual is None:
            return None
        aSeries, years = annual
        from dartlab.analysis.financial.ratios import calcRatioSeries, toSeriesDict

        rs = calcRatioSeries(aSeries, years)
        result = toSeriesDict(rs)
        self._company._cache[cacheKey] = result
        return result

    @property
    def SCE(self) -> pl.DataFrame | None:
        """SCE — TODO 한국어 동작 설명."""
        cacheKey = "_finance_SCE"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]
        from dartlab.providers.edgar.finance.pivot import buildSce

        result = buildSce(self._company.cik)
        self._company._cache[cacheKey] = result
        return result

    def explore(self, query: str) -> pl.DataFrame | None:
        """XBRL 태그 검색 — 전 기간 값 탐색."""
        from dartlab.providers.edgar.finance.explore import explore

        return explore(self._company.cik, query)

    def listTags(self, *, limit: int | None = None) -> pl.DataFrame | None:
        """보고된 모든 us-gaap 태그 목록.

        Args:
            limit: 최대 행 수. None 이면 무제한.

        Returns:
            태그 목록 DataFrame 또는 None.

        Example:
            >>> c.finance.listTags(limit=50)
        """
        from dartlab.providers.edgar.finance.explore import listTags

        return listTags(self._company.cik, limit=limit)

    def iterTags(self, *, limit: int | None = None):
        """``listTags`` 의 iterator pair (룰 10).

        Args:
            limit: 최대 행 수. None 이면 무제한.

        Yields:
            태그 row dict.

        Example:
            >>> for row in c.finance.iterTags(limit=20):
            ...     print(row["tag"], row["count"])
        """
        df = self.listTags(limit=limit)
        if df is None:
            return
        yield from df.iter_rows(named=True)
