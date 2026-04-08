"""finance authoritative namespace accessor.

company.py에서 분리된 accessor 클래스.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


class _FinanceAccessor:
    """finance authoritative namespace."""

    def __init__(self, company: "Company"):
        self._company = company

    @property
    def raw(self) -> pl.DataFrame | None:
        return self._company.rawFinance

    @property
    def BS(self) -> pl.DataFrame | None:
        return self._company._financeOrDocsStatement("BS")

    @property
    def IS(self) -> pl.DataFrame | None:
        return self._company._financeOrDocsStatement("IS")

    @property
    def CIS(self) -> pl.DataFrame | None:
        return self._company._financeOrDocsStatement("CIS")

    @property
    def CF(self) -> pl.DataFrame | None:
        return self._company._financeOrDocsStatement("CF")

    def timeseries(self, *, annual: bool = False, cumulative: bool = False):
        """finance 시계열 — 단일 진입점, 파라미터 토글 (api-contract).

        Args:
            annual: True 면 연도 단위 집계 (4분기 strict 합).
            cumulative: True 면 YTD 누적.
            둘 다 True 시 ValueError.
        """
        if annual and cumulative:
            raise ValueError("annual / cumulative 중 하나만 True 가능합니다.")
        if annual:
            return self._company._getFinanceBuild("y", "CFS")
        if cumulative:
            return self._company._getFinanceBuild("cum", "CFS")
        return self._company._getFinanceBuild("q", "CFS")

    @property
    def ratios(self):
        return self._company._getRatiosInternal("CFS")

    @property
    def ratioSeries(self):
        return self._company._ratioSeries()

    @property
    def SCE(self):
        return self._company._sce()

    @property
    def sceMatrix(self):
        return self._company._sceMatrix()
