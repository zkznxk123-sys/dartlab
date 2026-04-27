"""Deprecated — use ``dartlab.analysis.financial.attribution`` instead."""

from warnings import warn

from dartlab.analysis.financial.attribution import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.attribution → dartlab.analysis.financial.attribution (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
