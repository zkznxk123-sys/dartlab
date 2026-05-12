"""[INTERNAL] finance namespace accessor.

이 accessor 는 사용자 진입점이 **아니다**. 사용자는 ``c.show("IS", freq=, scope=)``
/ ``c.select(...)`` 만 사용해야 한다 (api-contract).

``company.py`` 의 ``_showFinanceTopic`` / ``_buildFinanceSeries`` 같은 내부 함수가
호출하는 backing namespace 일 뿐이다. property 4 개 (BS/IS/CF/CIS) 는 분기·연결
default 로만 호출되며 freq/scope 토글이 필요하면 ``_company._financeStmt(...)``
직접 호출.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


class _FinanceAccessor:
    """[INTERNAL] finance namespace — ``show()``/``select()`` 우회 금지."""

    def __init__(self, company: "Company"):
        self._company = company

    @property
    def raw(self) -> pl.DataFrame | None:
        """원본 finance parquet — XBRL 정규화 전 원본.

        Returns:
            raw row DataFrame 또는 None (데이터 부재).

        Raises:
            없음.

        Example:
            >>> c._finance.raw.head()  # 내부 호출만

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — internal namespace. 사용자 API 는 ``c.show("BS"/"IS"/"CF"/"CIS")``.
                - finance 부재 회사 → None.
            OutputSchema:
                - pl.DataFrame 또는 None.
            Prerequisites:
                - 본 회사 finance parquet 보유.
            Freshness:
                - finance 갱신 시점 (분기 마감 후 ~45 일).
            Dataflow:
                - finance parquet → 본 namespace.
            TargetMarkets:
                - KR (DART XBRL 정규화) 한정.
        """
        return self._company.rawFinance

    @property
    def BS(self) -> pl.DataFrame | None:
        """재무상태표 (Balance Sheet) — 시점 잔액 wide DataFrame.

        Returns:
            ``account`` 열 + period 열 wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.BS  # 내부 — 사용자는 c.show("BS")

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — internal namespace. 사용자 API 는 ``c.show("BS"/"IS"/"CF"/"CIS")``.
                - finance 부재 회사 → None.
            OutputSchema:
                - pl.DataFrame 또는 None.
            Prerequisites:
                - 본 회사 finance parquet 보유.
            Freshness:
                - finance 갱신 시점 (분기 마감 후 ~45 일).
            Dataflow:
                - finance parquet → 본 namespace.
            TargetMarkets:
                - KR (DART XBRL 정규화) 한정.
        """
        return self._company._financeOrDocsStatement("BS")

    @property
    def IS(self) -> pl.DataFrame | None:
        """손익계산서 (Income Statement) — 분기 standalone wide DataFrame.

        Returns:
            ``account`` 열 + period 열 wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.IS  # 내부 — 사용자는 c.show("IS")

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — internal namespace. 사용자 API 는 ``c.show("BS"/"IS"/"CF"/"CIS")``.
                - finance 부재 회사 → None.
            OutputSchema:
                - pl.DataFrame 또는 None.
            Prerequisites:
                - 본 회사 finance parquet 보유.
            Freshness:
                - finance 갱신 시점 (분기 마감 후 ~45 일).
            Dataflow:
                - finance parquet → 본 namespace.
            TargetMarkets:
                - KR (DART XBRL 정규화) 한정.
        """
        return self._company._financeOrDocsStatement("IS")

    @property
    def CIS(self) -> pl.DataFrame | None:
        """포괄손익계산서 (Comprehensive IS) — IS + OCI wide.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.CIS  # 내부 — 사용자는 c.show("CIS")

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — internal namespace. 사용자 API 는 ``c.show("BS"/"IS"/"CF"/"CIS")``.
                - finance 부재 회사 → None.
            OutputSchema:
                - pl.DataFrame 또는 None.
            Prerequisites:
                - 본 회사 finance parquet 보유.
            Freshness:
                - finance 갱신 시점 (분기 마감 후 ~45 일).
            Dataflow:
                - finance parquet → 본 namespace.
            TargetMarkets:
                - KR (DART XBRL 정규화) 한정.
        """
        return self._company._financeOrDocsStatement("CIS")

    @property
    def CF(self) -> pl.DataFrame | None:
        """현금흐름표 (Cash Flow) — 분기 standalone wide DataFrame.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.CF  # 내부 — 사용자는 c.show("CF")

        LLM Specifications:
            AntiPatterns:
                - 사용자 직접 호출 X — internal namespace. 사용자 API 는 ``c.show("BS"/"IS"/"CF"/"CIS")``.
                - finance 부재 회사 → None.
            OutputSchema:
                - pl.DataFrame 또는 None.
            Prerequisites:
                - 본 회사 finance parquet 보유.
            Freshness:
                - finance 갱신 시점 (분기 마감 후 ~45 일).
            Dataflow:
                - finance parquet → 본 namespace.
            TargetMarkets:
                - KR (DART XBRL 정규화) 한정.
        """
        return self._company._financeOrDocsStatement("CF")

    @property
    def ratios(self):
        """재무비율 (snapshot) — CFS 기본, 단일 period.

        Returns:
            ``RatioResult`` dataclass 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.ratios  # 내부 — 사용자는 c.show("ratios")
        """
        return self._company._getRatiosInternal("CFS")

    @property
    def ratioSeries(self):
        """재무비율 시계열 — 전 period 적용된 ratio.

        Returns:
            DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.ratioSeries  # 내부 — 사용자는 c.show("ratioSeries")
        """
        return self._company._ratioSeries()

    @property
    def SCE(self):
        """자본변동표 (Statement of Changes in Equity) — 시계열.

        Returns:
            wide DataFrame 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.SCE  # 내부 — 사용자는 c.show("SCE")
        """
        return self._company._sce()

    @property
    def sceMatrix(self):
        """SCE 매트릭스 — 연도 × 변동사유 × 자본항목 3D dict.

        Returns:
            ``matrix[year][cause][detail] = amount`` 구조 dict 또는 None.

        Raises:
            없음.

        Example:
            >>> c._finance.sceMatrix  # 내부 호출만
        """
        return self._company._sceMatrix()
