"""sections — DART 사전빌드 disclosure 보드 (runtime lazy read + BUILD).

요구 #5: sections = SSOT. show/diff/select/trace 는 이 위 얇은 derivation.

공개 표면 SSOT:
    - RUNTIME reader: ``scanSections`` / ``readSectionsMeta`` / ``readSectionsWide`` /
      ``readSectionsLong`` (scan_parquet 기반 lazy, lxml import 0).
    - schema 계약: ``SECTIONS_SCHEMA`` (14-col) / ``PIVOT_INDEX``.
    - BUILD: ``dartlab.providersV2.dart.sections.build`` 하위 (lxml/zip, BUILD 전용).

caller 는 본 표면만 import (deep leaf path 금지 — feedback_clean_module_tree).
"""

from __future__ import annotations

from .reader import (
    readSectionsLong,
    readSectionsMeta,
    readSectionsWide,
    scanSections,
)
from .schema import PIVOT_INDEX, SECTIONS_SCHEMA

__all__ = [
    "PIVOT_INDEX",
    "SECTIONS_SCHEMA",
    "readSectionsLong",
    "readSectionsMeta",
    "readSectionsWide",
    "scanSections",
]
