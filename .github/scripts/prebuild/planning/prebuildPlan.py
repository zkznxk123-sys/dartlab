"""Prebuild planning primitives.

Planning is pure and side-effect free. ``prebuildData.py`` performs the actual
HF listing, download, build, validation, and publish steps from these plans.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INCREMENTAL_DOWNLOAD_CAP = 8000


@dataclass(frozen=True)
class BaseSeedPlan:
    cachedCategories: tuple[str, ...]
    missingCategories: tuple[str, ...]


@dataclass(frozen=True)
class PanelDeltaPlan:
    processRel: tuple[str, ...]
    deferredRel: tuple[str, ...]
    removedRel: tuple[str, ...]
    changedCodes: tuple[str, ...]
    removedCodes: tuple[str, ...]
    newState: dict[str, int]
    bootstrap: bool
    capped: bool


def planBaseSeed(
    localCounts: Mapping[str, int],
    *,
    cacheFirstCategories: Sequence[str] = ("finance", "report"),
) -> BaseSeedPlan:
    """Plan cache-first base seeding for heavy full inputs."""
    cached: list[str] = []
    missing: list[str] = []
    for category in cacheFirstCategories:
        if localCounts.get(category, 0) > 0:
            cached.append(category)
        else:
            missing.append(category)
    return BaseSeedPlan(cachedCategories=tuple(cached), missingCategories=tuple(missing))


def planPanelDelta(
    prior: Mapping[str, int],
    remote: Mapping[str, int],
    *,
    cap: int = DEFAULT_INCREMENTAL_DOWNLOAD_CAP,
) -> PanelDeltaPlan:
    """Plan panel incremental download and next ledger state.

    Bootstrap cycles record the remote state without downloading every panel
    file. Capped cycles only advance the ledger for processed changed files so
    deferred files are re-detected on the next run.
    """
    if not prior:
        return PanelDeltaPlan(
            processRel=(),
            deferredRel=(),
            removedRel=(),
            changedCodes=(),
            removedCodes=(),
            newState=dict(remote),
            bootstrap=True,
            capped=False,
        )

    safeCap = max(0, int(cap))
    changedRel = tuple(sorted(rel for rel, size in remote.items() if prior.get(rel) != size))
    removedRel = tuple(sorted(rel for rel in prior if rel not in remote))
    processRel = changedRel[:safeCap]
    deferredRel = changedRel[safeCap:]

    newState = dict(prior)
    for rel in removedRel:
        newState.pop(rel, None)
    for rel in processRel:
        newState[rel] = remote[rel]

    return PanelDeltaPlan(
        processRel=processRel,
        deferredRel=deferredRel,
        removedRel=removedRel,
        changedCodes=tuple(sorted(Path(rel).stem for rel in processRel)),
        removedCodes=tuple(sorted(Path(rel).stem for rel in removedRel)),
        newState=newState,
        bootstrap=False,
        capped=bool(deferredRel),
    )
