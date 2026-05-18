"""quant 엔진 공용 헬퍼 — facade. 본체는 `_dataAccessOhlcv` / `_dataAccessScan` / `_dataAccessAccount`.

STOCK_CODE_COLUMNS · OHLCV fetch · market 감지 · scan parquet 로드 · 계정 추출.
"""

from __future__ import annotations

from ._dataAccessAccount import (
    _ACCOUNT_PATTERNS,
    _ACCOUNT_SJ,
    extractAccount,
    extractAccounts,
)
from ._dataAccessOhlcv import (
    extractSignalSeries,
    fetchBenchmark,
    fetchOhlcv,
    ohlcvToArrays,
    tomMask,
)
from ._dataAccessScan import (
    STOCK_CODE_COLUMNS,
    _scanDataRoot,
    loadAllfilingsForStock,
    loadChangesForStock,
    loadDocsForStock,
    loadScanParquet,
    loadSharesOutstanding,
    stockPercentile,
)

__all__ = [
    "STOCK_CODE_COLUMNS",
    "_ACCOUNT_PATTERNS",
    "_ACCOUNT_SJ",
    "_scanDataRoot",
    "extractAccount",
    "extractAccounts",
    "extractSignalSeries",
    "fetchBenchmark",
    "fetchOhlcv",
    "loadAllfilingsForStock",
    "loadChangesForStock",
    "loadDocsForStock",
    "loadScanParquet",
    "loadSharesOutstanding",
    "ohlcvToArrays",
    "stockPercentile",
    "tomMask",
]
