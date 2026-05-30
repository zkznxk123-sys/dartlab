"""DART/EDGAR 공통 docs 유틸리티."""

from dartlab.providers._common.diff import (
    DiffEntry,
    DiffResult,
    DiffSummary,
    LineDiff,
    buildDiffMatrix,
    buildHeatmapSpec,
    sectionsDiff,
    topicDiff,
)
from dartlab.reference.docs.bridge import (
    extractAmountsFromText,
    getFinanceAmounts,
    matchAmounts,
)
from dartlab.reference.docs.topicGraph import (
    analyzeGraph,
    buildMentionMatrix,
    getRelatedTopics,
)

__all__ = [
    "DiffEntry",
    "DiffResult",
    "DiffSummary",
    "LineDiff",
    "build_diff_matrix",
    "build_heatmap_spec",
    "sectionsDiff",
    "topicDiff",
    "extract_amounts_from_text",
    "get_finance_amounts",
    "match_amounts",
    "analyze_graph",
    "build_mention_matrix",
    "get_related_topics",
]
