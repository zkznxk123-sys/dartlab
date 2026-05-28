"""ECB Data Portal — Eurozone 거시지표 (SDMX-JSON).

Usage::

    from dartlab.gather.ecb import Ecb
    e = Ecb()
    m3 = e.series("ECB_M3")           # Eurozone M3
    cat = e.catalog()
"""

from __future__ import annotations

from .facade import Ecb

__all__ = ["Ecb"]
