"""Deprecated — use ``dartlab.quant.bottomUpBeta`` instead."""

from warnings import warn

from dartlab.quant.bottomUpBeta import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.bottomUpBeta → dartlab.quant.bottomUpBeta (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
