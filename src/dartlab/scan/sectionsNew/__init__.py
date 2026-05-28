"""L1.5 cross-market sections layer — Layer 3 bridge + 4 universal canonical.

마스터 플랜 v5 §1 + §2.1.
"""

from __future__ import annotations

from dartlab.scan.sectionsNew.bridgeLoader import (
    loadBridge,
    seedBridgeTier1,
)
from dartlab.scan.sectionsNew.canonicalResolver import resolveDisclosureKey
from dartlab.scan.sectionsNew.unifiedReader import (
    readSectionsLong,
    readSectionsWide,
)

__all__ = [
    "loadBridge",
    "readSectionsLong",
    "readSectionsWide",
    "resolveDisclosureKey",
    "seedBridgeTier1",
]
