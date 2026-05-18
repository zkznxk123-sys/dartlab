"""valuation.py 깊이 — facade. 본체는 `_valuationDeepProxies` / `_valuationDeepFuncs`.

calcPriceTarget + _classifyCompanyType + calcValuationSynthesis + calcValuationFlags
+ 16 lazy proxy. valuation.py 본체에서 BC re-export.
"""

from __future__ import annotations

from dartlab.analysis.financial._valuationDeepFuncs import (
    _classifyCompanyType,
    calcPriceTarget,
    calcValuationFlags,
    calcValuationSynthesis,
)
from dartlab.analysis.financial._valuationDeepProxies import (
    __getattr__,
    _fetchPriceContext,
    _getSectorParams,
    _getSeriesAndShares,
    _inRange,
    _resolveSectorKey,
    _rimCalc,
    calcCrossSectionRegression,
    calcDcf,
    calcDdm,
    calcMonteCarloValuation,
    calcNavValuation,
    calcRelativeValuation,
    calcResidualIncome,
    calcReverseImplied,
    calcSensitivity,
    calcValuationConsistency,
    computePriceTarget,
)

__all__ = [
    "_classifyCompanyType",
    "_fetchPriceContext",
    "_getSectorParams",
    "_getSeriesAndShares",
    "_inRange",
    "_resolveSectorKey",
    "_rimCalc",
    "calcCrossSectionRegression",
    "calcDcf",
    "calcDdm",
    "calcMonteCarloValuation",
    "calcNavValuation",
    "calcPriceTarget",
    "calcRelativeValuation",
    "calcResidualIncome",
    "calcReverseImplied",
    "calcSensitivity",
    "calcValuationConsistency",
    "calcValuationFlags",
    "calcValuationSynthesis",
    "computePriceTarget",
]
