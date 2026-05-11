"""edgar/bulk LoaderProvider 구현 (정공법 B — DIP).

`core/dataLoader.py` 가 직접 ensureFinanceParquet 호출 대신 registry dispatch.
import 시점에 registerLoader 호출하여 자동 등록.
"""

from __future__ import annotations

from dartlab.providers.edgar.bulk.companyfactsBulk import ensureFinanceParquet


class EdgarBulkLoader:
    """edgar 카테고리의 LoaderProvider 구현 (SEC 벌크 finance)."""

    category = "edgar"

    def ensure(self, stockCode, path, *, sinceYear=None, asOf=None, refresh="auto"):
        """SEC 벌크 finance parquet 보장 — ensureFinanceParquet 위임."""
        ensureFinanceParquet(stockCode, path, refresh=bool(refresh and refresh != "auto"))


def registerEdgarBulkLoader() -> None:
    """edgar/bulk LoaderProvider 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.loaders import registerLoader

    registerLoader(EdgarBulkLoader())
