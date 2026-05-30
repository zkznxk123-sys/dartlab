"""sections — DART 사전빌드 disclosure 보드 (RUNTIME lazy read).

요구 #5: sections = SSOT. show/diff/select/trace 는 이 위 얇은 derivation.
read-only plane — 네트워크·BUILD 0.

공개 표면 SSOT:
    - RUNTIME reader: ``scanSections`` / ``readSectionsMeta`` / ``readSectionsWide`` /
      ``readSectionsLong`` (scan_parquet 기반 lazy, lxml import 0).
    - read-side 앵커: ``scopeExpr`` / ``anchorLatest`` (최신기준 과거 수평화, 요구 #7).
    - schema 계약 (14-col) / ``PIVOT_INDEX``: ``dartlab.core.sections`` 재노출.
    - BUILD: ``dartlab.gather.dart.sections.build`` (lxml/zip, acquire+produce plane).

caller 는 본 표면만 import (deep leaf path 금지 — feedback_clean_module_tree).
"""

from __future__ import annotations

from dartlab.core.sections import PIVOT_INDEX, SECTIONS_SCHEMA

from .anchor import anchorLatest, scopeExpr
from .reader import (
    readSectionsLong,
    readSectionsMeta,
    readSectionsWide,
    scanSections,
)

__all__ = [
    "PIVOT_INDEX",
    "SECTIONS_SCHEMA",
    "anchorLatest",
    "readSectionsLong",
    "readSectionsMeta",
    "readSectionsWide",
    "scanSections",
    "scopeExpr",
]
