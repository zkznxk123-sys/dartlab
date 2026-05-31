"""panel 획득+생산 (L1 gather) — 빌드·학습·인덱스·오케스트레이션.

DART zip → panel 14-col artifact 생산 owner. network·write·무거운 수평화는 본 gather
층에 격리 (reader 는 로컬 artifact read only, R2). core.panel 계약만 의존 — providers
import 0 (gather ↛ providers, R1 · core_boundary). 수집(zip)·HF push 는 CI entry
(.github/scripts/sync, layer-밖) 가 앞뒤로 묶음.

공개표면 SSOT (deep leaf import 금지, R6):
    - ``buildPanel`` / ``buildPanelAll`` / ``buildPanelBaseline`` (build, 로컬 zip→parquet).
    - ``buildPanelFromStream`` (online 1패스 — (rcept,bytes) 스트림 → parquet, 디스크 zip 0).
    - ``buildIndex`` / ``indexPath`` / ``panelXbrlRefPath`` (slim 인덱스 + 경로 SSOT).
    - ``buildLabel`` / ``labelPath`` (canonicalKey → 한글 표시라벨 _label.parquet).
    - ``syncPanel`` (refScan→build→index→label 오케스트레이션).

bridge-learning(learnBridge)은 2026-05 redesign 으로 폐기 — KR 정렬키는 core.panel.canonicalKey
(native ACLASS), bridge 는 US cross-market overlay 전용(core.panel.seedBridgeTier1, 운영자).
"""

from __future__ import annotations

from .build import buildPanel, buildPanelAll, buildPanelBaseline, buildPanelFromStream
from .index import buildIndex, buildLabel, indexPath, labelPath, panelXbrlRefPath
from .sync import syncPanel

__all__ = [
    "buildIndex",
    "buildLabel",
    "buildPanel",
    "buildPanelAll",
    "buildPanelBaseline",
    "buildPanelFromStream",
    "indexPath",
    "labelPath",
    "panelXbrlRefPath",
    "syncPanel",
]
