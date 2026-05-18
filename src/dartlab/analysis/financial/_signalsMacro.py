"""구조변화 + 매크로 신호 — facade. 본체는 `_signalsMacroBreak` / `_signalsMacroSensitivity`.

calcStructuralBreak: Chow Test 기반 매출/영업이익/마진/ROE 구조변화점 감지.
calcMacroSensitivity: 섹터별 탄성치 + 매크로 지표 매핑.
calcMacroRegression: OLS 외생변수 회귀로 베타 추정.
"""

from __future__ import annotations

from dartlab.analysis.financial._signalsMacroBreak import (
    _getStockCode,
    calcStructuralBreak,
)
from dartlab.analysis.financial._signalsMacroSensitivity import (
    _COMMODITY_SECTORS,
    _FX_SENSITIVE_SECTORS,
    _RATE_SENSITIVE_SECTORS,
    _SECTOR_DATA,
    _SECTOR_MACRO_MAP,
    _avgGrowth,
    _buildMacroTable,
    _getFinanceSeries,
    _getRatioValues,
    _getSectorKey,
    _loadAdaptive,
    _loadMacroAligned,
    _predictDirection,
    calcMacroRegression,
    calcMacroSensitivity,
)

__all__ = [
    "_COMMODITY_SECTORS",
    "_FX_SENSITIVE_SECTORS",
    "_RATE_SENSITIVE_SECTORS",
    "_SECTOR_DATA",
    "_SECTOR_MACRO_MAP",
    "_avgGrowth",
    "_buildMacroTable",
    "_getFinanceSeries",
    "_getRatioValues",
    "_getSectorKey",
    "_getStockCode",
    "_loadAdaptive",
    "_loadMacroAligned",
    "_predictDirection",
    "calcMacroRegression",
    "calcMacroSensitivity",
    "calcStructuralBreak",
]
