"""Vectorized technical indicators grouped by market behavior.

Capabilities:
    - Public compatibility surface for ``from dartlab.core.indicators import ...``.
    - Re-exports grouped indicator implementations from trend, momentum, volatility,
      channels, volume, and price modules.

Args:
    This package exposes functions. Each function accepts NumPy float arrays and period
    parameters documented on the concrete implementation.

Returns:
    Indicator arrays or tuples of arrays with the same length as the input price series.

Example:
    >>> from dartlab.core.indicators import vsma, vrsi, vmacd
    >>> sma = vsma(close, period=20)

Guide:
    Keep this module thin. Add new indicator implementations to a behavior group module,
    then re-export here for public API stability.

SeeAlso:
    ``trend`` for averages/trend strength, ``momentum`` for oscillators, ``volume`` for
    volume pressure, ``channels`` for price bands, ``volatility`` for range/risk, and
    ``price`` for price-shape helpers.

Requires:
    NumPy arrays with aligned lengths. This package does not fetch market data.

AIContext:
    L2 quant and scan callers can depend on this package as the stable L1.5 indicator
    catalog without importing group internals.

LLM Specifications:
    AntiPatterns: Do not add data fetching, provider access, scan calls, or frame logic here.
    OutputSchema: Public functions return NDArray[np.float64] or tuples of such arrays.
    Prerequisites: Caller provides clean OHLCV arrays and handles insufficient history.
    Freshness: Pure calculation only; freshness is inherited from caller-provided arrays.
    Dataflow: caller OHLCV arrays -> grouped indicator function -> NumPy output arrays.
    TargetMarkets: Any OHLCV-like market series; no Korea-specific assumptions.
"""

from __future__ import annotations

from dartlab.core.indicators.channels import (
    vbollinger,
    vbollingerPercentB,
    vbollingerWidth,
    vdonchian,
    vkeltner,
)
from dartlab.core.indicators.momentum import (
    vawesomeOscillator,
    vcci,
    vcmo,
    vdpo,
    vkdj,
    vmomentum,
    vroc,
    vrsi,
    vstochastic,
    vstochasticRsi,
    vultimateOscillator,
    vwilliamsR,
)
from dartlab.core.indicators.price import vlinearRegression, vpivotPoints, vzigzag
from dartlab.core.indicators.trend import (
    vadx,
    vdema,
    vema,
    vhma,
    vmacd,
    vpsar,
    vsma,
    vsupertrend,
    vtema,
    vtrix,
    vvwma,
    vwma,
)
from dartlab.core.indicators.volatility import vatr, vulcer
from dartlab.core.indicators.volume import (
    vadl,
    vchaikin,
    velderRay,
    vemv,
    vforceIndex,
    vmfi,
    vnvi,
    vobv,
    vpvi,
    vpvt,
    vvwap,
)

__all__ = [
    "vadl",
    "vadx",
    "vatr",
    "vawesomeOscillator",
    "vbollinger",
    "vbollingerPercentB",
    "vbollingerWidth",
    "vcci",
    "vchaikin",
    "vcmo",
    "vdema",
    "vdonchian",
    "vdpo",
    "velderRay",
    "vema",
    "vemv",
    "vforceIndex",
    "vhma",
    "vkeltner",
    "vkdj",
    "vlinearRegression",
    "vmacd",
    "vmfi",
    "vmomentum",
    "vnvi",
    "vobv",
    "vpivotPoints",
    "vpsar",
    "vpvi",
    "vpvt",
    "vroc",
    "vrsi",
    "vsma",
    "vstochastic",
    "vstochasticRsi",
    "vsupertrend",
    "vtema",
    "vtrix",
    "vultimateOscillator",
    "vulcer",
    "vvwap",
    "vvwma",
    "vwilliamsR",
    "vwma",
    "vzigzag",
]
