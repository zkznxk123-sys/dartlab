"""EDGAR panel canonical facade — shared read-time chapter/rank skeleton."""

from __future__ import annotations

from dartlab.providers.dart.panel.canonical import (
    CANONICAL_L1,
    CANONICAL_RANK,
    CERT_NODE_IDS,
    REPORT_CHAPTER_LABELS,
    canonicalChapterExpr,
    canonicalRankExpr,
)

__all__ = [
    "CANONICAL_L1",
    "CANONICAL_RANK",
    "CERT_NODE_IDS",
    "REPORT_CHAPTER_LABELS",
    "canonicalChapterExpr",
    "canonicalRankExpr",
]
