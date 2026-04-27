"""Deprecated — use ``dartlab.analysis.financial.quality`` instead."""

from warnings import warn

from dartlab.analysis.financial.quality import *  # noqa: F401, F403

warn(
    "dartlab.core.finance.quality → dartlab.analysis.financial.quality (deprecated, removed in next major)",
    DeprecationWarning,
    stacklevel=2,
)
