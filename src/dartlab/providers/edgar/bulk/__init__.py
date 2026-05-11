"""SEC EDGAR 벌크 기반 finance 수집.

dartlab의 EDGAR finance primary 소스는 SEC 벌크다:
- daily: ``Archives/edgar/daily-index/xbrl/companyfacts.zip``
- quarterly: ``files/dera/data/financial-statement-data-sets/{Y}q{Q}.zip``

상세: ``engines.edgar``.
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
from dartlab.providers.edgar.bulk.loader import EdgarBulkLoader, registerEdgarBulkLoader

__all__ = [
    "DATASET_FILES",
    "BulkFreshness",
    "EdgarBulkLoader",
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
    "listLocalQuarters",
    "readSavedEtag",
    "touchBulkFreshness",
]

registerEdgarBulkLoader()
