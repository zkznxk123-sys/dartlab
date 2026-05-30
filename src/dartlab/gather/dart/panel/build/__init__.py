"""panel BUILD 공개표면 (L1 gather, write) — zip → 14-col parquet 생산.

caller 는 ``from dartlab.gather.dart.panel.build import buildPanel`` 만 (deep leaf
import 금지, R6). lxml·zipfile 사용은 본 build 패키지에 격리 (reader 는 scan_parquet 만, R2).

공개:
    - ``buildPanel`` / ``buildPanelAll`` / ``buildPanelBaseline`` (builder).
    - ``horizontalize`` (element→section 무손실 concat).
    - ``walkSections`` / ``detectSchemaEra`` (walker).
    - ``scanAllZips`` / ``scanRefBaseline`` / ``scanZipFiles`` (refScan, ref truth 생산).
"""

from __future__ import annotations

from .builder import buildPanel, buildPanelAll, buildPanelBaseline
from .horizontalize import horizontalize
from .refScan import scanAllZips, scanRefBaseline, scanZipFiles
from .walker import detectSchemaEra, walkSections

__all__ = [
    "buildPanel",
    "buildPanelAll",
    "buildPanelBaseline",
    "detectSchemaEra",
    "horizontalize",
    "scanAllZips",
    "scanRefBaseline",
    "scanZipFiles",
    "walkSections",
]
