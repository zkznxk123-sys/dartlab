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
from .index import buildIndex, indexPath
from .learn import bridgeCoverage, learnBridge

__all__ = [
    "bridgeCoverage",
    "buildIndex",
    "buildPanel",
    "buildPanelAll",
    "buildPanelBaseline",
    "indexPath",
    "learnBridge",
    "panelXbrlRefPath",
]


def panelXbrlRefPath() -> "Path":  # noqa: F821
    """panelXbrlRef ref table 경로 — refScan 산출 + build/learn 입력 SSOT.

    Args:
        없음.

    Returns:
        ``data/dart/panelXbrlRef.parquet`` Path.

    Raises:
        없음.

    Example:
        >>> panelXbrlRefPath().name
        'panelXbrlRef.parquet'

    SeeAlso:
        - ``build.refScan.scanAllZips`` — 본 경로 생산.
        - ``learn.learnBridge`` — 본 ref 로 학습.
        - ``build.buildPanelAll`` — 본 ref 로 fuzzy 매칭.

    Requires:
        - dartlab.config.

    Capabilities:
        - ref truth(S4) 단일 경로 — refScan write·build/learn read 공유.

    Guide:
        - refScan 후 build/learn 이 본 경로 참조.

    AIContext:
        - 경로 계산만.

    LLM Specifications:
        AntiPatterns:
            - 경로 분산 하드코딩 금지.
        OutputSchema:
            - ``pathlib.Path``.
        Prerequisites:
            - config.dataDir.
        Freshness:
            - 정적.
        Dataflow:
            - config.dataDir → data/dart/panelXbrlRef.parquet.
        TargetMarkets:
            - KR (DART).
    """
    from pathlib import Path

    import dartlab.config as _cfg

    return Path(_cfg.dataDir) / "dart" / "panelXbrlRef.parquet"
