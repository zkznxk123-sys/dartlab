"""SEC EDGAR 벌크 기반 finance 수집.

dartlab의 EDGAR finance primary 소스는 SEC 벌크다:
- daily: `Archives/edgar/daily-index/xbrl/companyfacts.zip` (1.37GB, 매일 04:25 UTC)
- quarterly: `files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip` (sub/pre/tag TSV)

`data.sec.gov/api/xbrl/companyfacts` API는 사용자 선택 경로의 내부 refresh 만 사용한다 —
자동 파이프라인 비사용.

num.tsv는 받지 않는다 — companyfacts.zip이 같은 값의 더 신선한 번들.

상세: `engines.edgar`.
"""

from dartlab.providers.edgar.bulk.companyfactsBulk import (
    convertBulkToParquets,
    downloadCompanyfactsBulk,
    ensureFinanceParquet,
    extractCompanyfactsZip,
)
from dartlab.providers.edgar.bulk.datasetBulk import (
    DATASET_FILES,
    convertQuarterlyToParquets,
    discoverLatestQuarter,
    downloadQuarterlyDataset,
    listLocalQuarters,
)
from dartlab.providers.edgar.bulk.freshness import (
    BulkFreshness,
    inspectBulkFreshness,
    invalidateBulkFreshness,
    isBulkFresh,
    readSavedEtag,
    touchBulkFreshness,
)

__all__ = [
    "DATASET_FILES",
    "BulkFreshness",
    "convertBulkToParquets",
    "convertQuarterlyToParquets",
    "discoverLatestQuarter",
    "downloadCompanyfactsBulk",
    "downloadQuarterlyDataset",
    "ensureFinanceParquet",
    "extractCompanyfactsZip",
    "inspectBulkFreshness",
    "invalidateBulkFreshness",
    "isBulkFresh",
    "readSavedEtag",
    "listLocalQuarters",
    "touchBulkFreshness",
]


# ── LoaderProvider 구현 + register (정공법 B — DIP) ─────────────


class EdgarBulkLoader:
    """edgar 카테고리의 LoaderProvider 구현 (SEC 벌크 finance).

    core/dataLoader.py 가 직접 ensureFinanceParquet 호출 대신 registry dispatch.
    """

    category = "edgar"

    def ensure(self, stockCode, path, *, sinceYear=None, asOf=None, refresh="auto"):
        """SEC 벌크 finance parquet 보장 — ensureFinanceParquet 위임."""
        ensureFinanceParquet(stockCode, path, refresh=bool(refresh and refresh != "auto"))


def _registerEdgarBulkLoader() -> None:
    """import 시점 등록 — circular import 회피용 함수 lazy import."""
    from dartlab.core.loaders import registerLoader

    registerLoader(EdgarBulkLoader())


_registerEdgarBulkLoader()
