"""BIS (Bank for International Settlements) — 글로벌 통화·신용·환율 (SDMX-JSON).

Usage::

    from dartlab.gather.bis import Bis
    b = Bis()
    rate = b.series("BIS_POLICY_RATE_US")
"""

from __future__ import annotations

from .facade import Bis

__all__ = ["Bis"]
