"""Research 서사 dataclasses — types.py 에서 분리.

NarrativeParagraph + NarrativeAnalysis 교차분석 서술 결과.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ══════════════════════════════════════
# Narrative Analysis — v3
# ══════════════════════════════════════


@dataclass
class NarrativeParagraph:
    """단일 교차분석 서술 단위."""

    dimension: str = ""  # "dupont"|"margin"|"growth"|"cashflow"|"efficiency"|"segment"|"sectorRelative"
    title: str = ""
    body: str = ""  # 2-3문장 교차분석 서술
    severity: str = ""  # "positive"|"neutral"|"negative"|"warning"


@dataclass
class NarrativeAnalysis:
    """7차원 교차분석 서술 결과."""

    paragraphs: list[NarrativeParagraph] = field(default_factory=list)
    forwardImplications: list[str] = field(default_factory=list)
    crossReferences: list[str] = field(default_factory=list)
