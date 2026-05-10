"""종목 검색 ListingResolver Protocol — DIP (정공법 B).

core/resolve.py 가 gather/listing.py 직접 import 하지 않고 registry 로 접근.
gather/listing.py 가 ListingResolverImpl 등록.

dartKey CredentialProvider, EdgarLoader 와 동일 패턴 (FastAPI startup tasks).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import polars as pl


@runtime_checkable
class ListingResolver(Protocol):
    """종목 (회사명 ↔ stockCode) 검색 추상화.

    구현 위치: gather/listing.py 의 GatherListingResolver.
    """

    def search(self, query: str) -> "pl.DataFrame | None":
        """회사명 substring/prefix 검색."""
        ...

    def fuzzy(self, query: str, *, maxResults: int = 5) -> "pl.DataFrame | None":
        """초성/Levenshtein fuzzy 검색."""
        ...


_RESOLVER: ListingResolver | None = None

# Auto-discovery — gather/listing.py 가 register 하도록 lazy 로드.
_KNOWN_RESOLVER_MODULES: tuple[str, ...] = ("dartlab.gather.listing",)
_DISCOVERED = False


def _discover() -> None:
    """알려진 ListingResolver 모듈을 한 번만 lazy import — register 트리거."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    import importlib

    for modPath in _KNOWN_RESOLVER_MODULES:
        try:
            importlib.import_module(modPath)
        except ImportError:
            continue
    _DISCOVERED = True


def registerListingResolver(resolver: ListingResolver) -> None:
    """ListingResolver 등록 — gather/listing 가 import 시점에 호출."""
    global _RESOLVER
    _RESOLVER = resolver


def getListingResolver() -> ListingResolver | None:
    """현재 등록된 ListingResolver. 미등록이면 None. auto-discovery 트리거."""
    _discover()
    return _RESOLVER
