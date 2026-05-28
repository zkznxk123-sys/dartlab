"""IMF SDMX — 글로벌 거시 + 환율 + BOP (SDMX-JSON sdmxcentral.imf.org).

Usage::

    from dartlab.gather.imf import Imf
    i = Imf()
    fx = i.series("IMF_FX_USD_KRW")
"""

from __future__ import annotations

from .facade import Imf

__all__ = ["Imf"]
