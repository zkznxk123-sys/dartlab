"""EDGAR parse — iXBRL viewer + diff + horizontalize.

Implementation status
---------------------
- 구현 완료 (v1): iXbrlViewer / diffEvaluator / tableHorizontalizer.
- 대응 dart 모듈: ``providers/dart/parse/`` (4 파일 / 1043 줄).

공개 surface:
- iXbrlViewer: ``extractIxbrlFacts`` / ``fetchFactsByConcept`` / ``iterFactsByConcept``
- diffEvaluator: ``textSimilarity`` / ``evaluateDiff`` / ``fetchDiffRows`` / ``iterDiffRows``
- tableHorizontalizer: ``horizontalizeFacts`` / ``fetchHorizontalSlice`` / ``iterHorizontalSlice``
"""

from dartlab.providers.edgar.parse.diffEvaluator import (
    evaluateDiff,
    fetchDiffRows,
    iterDiffRows,
    textSimilarity,
)
from dartlab.providers.edgar.parse.iXbrlViewer import (
    extractIxbrlFacts,
    fetchFactsByConcept,
    iterFactsByConcept,
)
from dartlab.providers.edgar.parse.tableHorizontalizer import (
    fetchHorizontalSlice,
    horizontalizeFacts,
    iterHorizontalSlice,
)

__all__ = [
    "extractIxbrlFacts",
    "fetchFactsByConcept",
    "iterFactsByConcept",
    "textSimilarity",
    "evaluateDiff",
    "fetchDiffRows",
    "iterDiffRows",
    "horizontalizeFacts",
    "fetchHorizontalSlice",
    "iterHorizontalSlice",
]
