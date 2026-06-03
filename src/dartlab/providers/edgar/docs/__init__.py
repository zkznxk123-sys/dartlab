"""EDGAR 공시 문서 저장소 엔진.

현재 단계는 저장 규약, 로더 연동, sections horizontal view까지 포함한다.
개별 disclosure 파서는 experiments/055_edgarDocs, 057_edgarSectionMap 결과를 바탕으로 순차 흡수한다.

NOTE: fetchEdgarDocs/downloadListedEdgarDocs(SEC HTML fetch)는 gather/edgar/docs 로 이관 —
lazy ``__getattr__`` re-export(providers↛gather module-level 회피). sections(build)는 providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dartlab.providers.edgar.docs.sections import sections

if TYPE_CHECKING:
    from dartlab.gather.edgar.docs.fetch import downloadListedEdgarDocs, fetchEdgarDocs

__all__ = ["fetchEdgarDocs", "downloadListedEdgarDocs", "sections"]

_LAZY = {
    "fetchEdgarDocs": "dartlab.gather.edgar.docs.fetch",
    "downloadListedEdgarDocs": "dartlab.gather.edgar.docs.fetch",
}


def __getattr__(name: str):
    """lazy re-export — SEC docs fetch 를 접근 시점에만 gather 에서 import."""
    import importlib

    modPath = _LAZY.get(name)
    if modPath is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(modPath), name)
