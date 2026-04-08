"""[INTERNAL] finance namespace accessor.

이 accessor 는 사용자 진입점이 **아니다**. 사용자는 ``c.show("IS", freq=, scope=)``
/ ``c.select(...)`` 만 사용해야 한다 (api-contract).

company.py 의 ``_showFinanceTopic`` / ``_buildFinanceSeries`` 같은 내부 함수가
호출하는 backing namespace 일 뿐이다. property 4개 (BS/IS/CF/CIS) 는 분기·연결
default 로만 호출되며 freq/scope 토글이 필요하면 ``_company._financeStmt(...)``
직접 호출.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from dartlab.providers.dart.company import Company


class _FinanceAccessor:
    """[INTERNAL] finance namespace — show()/select() 우회 금지."""

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
