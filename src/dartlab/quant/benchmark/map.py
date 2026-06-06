"""Benchmark map 호환 경로.

SSOT는 ``dartlab.synth.benchmarkMap``에 있다.
"""

from __future__ import annotations

from dartlab.synth.benchmarkMap import (
    INDEX_ALIASES,
    SECTOR_INDEX_MAP,
    availableIndexNames,
    indexExists,
    loadIndustryNodes,
    primaryIndustryNode,
    sectorCandidates,
)

__all__ = [
    "INDEX_ALIASES",
    "SECTOR_INDEX_MAP",
    "availableIndexNames",
    "indexExists",
    "loadIndustryNodes",
    "primaryIndustryNode",
    "sectorCandidates",
]
