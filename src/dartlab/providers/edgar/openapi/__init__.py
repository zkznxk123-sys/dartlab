"""EDGAR OpenAPI facade (compat shim).

from dartlab import OpenEdgar

e = OpenEdgar()
aapl = e("AAPL")

aapl.info()
aapl.filings(forms=["10-K", "10-Q"])
aapl.companyFactsJson()
aapl.saveDocs()
aapl.saveFinance()

NOTE: OpenEdgar 파사드는 gather/edgar 로 이관(SEC fetch 전담) — 본 패키지는 lazy
``__getattr__`` re-export shim(providers↛gather module-level 회피). 공개명
``dartlab.OpenEdgar`` 보존.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dartlab.gather.edgar.edgar import OpenEdgar, OpenEdgarCompany

__all__ = ["OpenEdgar", "OpenEdgarCompany"]

_LAZY = {
    "OpenEdgar": "dartlab.gather.edgar.edgar",
    "OpenEdgarCompany": "dartlab.gather.edgar.edgar",
}


def __getattr__(name: str):
    """lazy re-export — OpenEdgar 파사드를 접근 시점에만 gather 에서 import."""
    import importlib

    modPath = _LAZY.get(name)
    if modPath is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(modPath), name)
