"""OECD SDMX — G20 거시지표 (SDMX-JSON sdmx.oecd.org 신 endpoint).

Usage::

    from dartlab.gather.oecd import Oecd
    o = Oecd()
    cpi = o.series("OECD_CPI_US")
"""

from __future__ import annotations

from .facade import Oecd

__all__ = ["Oecd"]
