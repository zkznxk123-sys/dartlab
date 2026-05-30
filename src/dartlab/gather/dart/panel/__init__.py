"""panel 획득+생산 (L1 gather) — 수집·빌드·학습·인덱스·HF 업로드.

DART zip → panel 14-col artifact 생산 owner. network·write·무거운 수평화는 본 gather
층에 격리 (reader 는 로컬 artifact read only, R2). core.panel 계약만 의존 — providers
import 0 (gather ↛ providers, R1 · core_boundary).

공개표면 SSOT (deep leaf import 금지, R6):
    - ``buildPanel`` / ``buildPanelAll`` / ``buildPanelBaseline`` (build, zip→parquet).
    - (P3+) ``learnBridge`` (bridge-learning) · ``buildIndex`` (slim 인덱스) ·
      ``collectZips`` (수집) · ``uploadPanel`` (HF) · ``syncPanel`` (오케스트레이션).
"""

from __future__ import annotations

from .build import buildPanel, buildPanelAll, buildPanelBaseline
from .learn import bridgeCoverage, learnBridge

__all__ = [
    "bridgeCoverage",
    "buildPanel",
    "buildPanelAll",
    "buildPanelBaseline",
    "learnBridge",
]
