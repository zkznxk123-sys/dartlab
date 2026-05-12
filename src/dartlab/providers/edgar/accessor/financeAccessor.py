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
        """재무제표 DataFrame. ``freq="Q"`` (분기, 기본) 또는 ``"Y"`` (연간).

        Args:
            stmtKey: BS/IS/CF/CI 중 하나.
            freq: ``"Q"``/``"Y"``.

        Returns:
            ``snakeId/항목/period...`` 컬럼 wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance._stmtDf("BS")
        """
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
        """재무상태표 (Balance Sheet) — XBRL companyfacts 기반.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.BS  # 내부 — 사용자는 c.show("BS")

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        return self._stmtDf("BS")

    @property
    def IS(self) -> pl.DataFrame | None:
        """손익계산서 (Income Statement) — XBRL companyfacts 기반.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.IS  # 내부 — 사용자는 c.show("IS")

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        return self._stmtDf("IS")

    @property
    def CF(self) -> pl.DataFrame | None:
        """현금흐름표 (Cash Flow) — XBRL companyfacts 기반.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.CF  # 내부 — 사용자는 c.show("CF")

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        return self._stmtDf("CF")

    @property
    def CIS(self) -> pl.DataFrame | None:
        """포괄손익계산서 (Comprehensive IS) — IS + OCI.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.CIS  # 내부 — 사용자는 c.show("CIS")

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        return self._stmtDf("CI")

    @property
    def ratios(self):
        """재무비율 snapshot — 연간 base.

        Returns:
            ``RatioResult`` dataclass 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.ratios  # 내부 — 사용자는 c.show("ratios")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>
        """
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
        """재무비율 시계열 — 연간 series.

        Returns:
            ``{ratio: [년도별 값...], ...}`` dict 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.ratioSeries  # 내부 — 사용자는 c.show("ratioSeries")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>
        """
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
        """자본변동표 (Statement of Changes in Equity).

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.SCE  # 내부 — 사용자는 c.show("SCE")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        cacheKey = "_finance_SCE"
        if cacheKey in self._company._cache:
            return self._company._cache[cacheKey]
        from dartlab.providers.edgar.finance.pivot import buildSce

        result = buildSce(self._company.cik)
        self._company._cache[cacheKey] = result
        return result

    def explore(self, query: str) -> pl.DataFrame | None:
        """XBRL 태그 검색 — 전 기간 값 탐색.

        Args:
            query: 태그 패턴 (정규식 또는 substring).

        Returns:
            매칭 행 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.explore("Revenue")

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.edgar.finance.explore import explore

        return explore(self._company.cik, query)

    def listTags(self, *, limit: int | None = None) -> pl.DataFrame | None:
        """보고된 모든 us-gaap 태그 목록.

        Args:
            limit: 최대 행 수. None 이면 무제한.

        Returns:
            태그 목록 DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.listTags(limit=50)

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        from dartlab.providers.edgar.finance.explore import listTags

        return listTags(self._company.cik, limit=limit)

    def iterTags(self, *, limit: int | None = None):
        """``listTags`` 의 iterator pair (룰 10).

        Args:
            limit: 최대 행 수. None 이면 무제한.

        Yields:
            태그 row dict.

        Raises:
            없음.

        Example:
            >>> for row in c._finance.iterTags(limit=20):
            ...     print(row["tag"], row["count"])

        SeeAlso:
            - <TODO: 관련 함수/엔진>

        Requires:
            - dartlab
            - polars

        Capabilities:
            - <TODO: 함수 핵심 책임 요약>

        Guide:
            - <TODO: 사용 시나리오>

        AIContext:
            <TODO: AI 호출 컨텍스트>

        LLM Specifications:
            AntiPatterns:
                - <TODO: 안티패턴>
            OutputSchema:
                - <TODO: 출력 형태>
            Prerequisites:
                - <TODO: 사전조건>
            Freshness:
                - <TODO: 데이터 freshness>
            Dataflow:
                - <TODO: 데이터 흐름>
            TargetMarkets:
                - <TODO: 대상 시장>
        """
        df = self.listTags(limit=limit)
        if df is None:
            return
        yield from df.iter_rows(named=True)
