"""Prebuild manifest helpers.

The CI script keeps IO orchestration in ``prebuildData.py``. This module holds
small deterministic helpers for artifact paths and local category counts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

SCAN_BASE_ARTIFACTS: tuple[str, ...] = (
    "changes.parquet",
    "finance.parquet",
    "finance-lite.parquet",
    "sharesOutstanding.parquet",
    "docsIndex.parquet",
    "corpProfile.parquet",
    "_scanBuildState.json",
)


def categoryFileCount(dataDir: str, category: str, dataReleases: Mapping[str, Mapping[str, str]]) -> int:
    """Return local file count for a released data category."""
    catDir = Path(dataDir) / dataReleases[category]["dir"]
    return sum(1 for p in catDir.rglob("*") if p.is_file()) if catDir.exists() else 0


def scanArtifactRelPaths(scanDir: str, reportApiTypes: Sequence[str]) -> list[str]:
    """Return fixed scan artifact paths without opening HF tree listing."""
    rels = [f"{scanDir}/{name}" for name in SCAN_BASE_ARTIFACTS]
    rels.extend(f"{scanDir}/report/{apiType}.parquet" for apiType in reportApiTypes)
    return rels
