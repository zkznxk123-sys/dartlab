"""사업보고서 섹션 구조화 모듈."""

from dartlab.providers.dart.docs.sectionsLegacy.analysis import (
    projectFreqRows,
    semanticCollisions,
    semanticRegistry,
    structureChanges,
    structureCollisions,
    structureEvents,
    structureRegistry,
    structureSummary,
)
from dartlab.providers.dart.docs.sectionsLegacy.extractors import (
    ParsedSubtopicTable,
    TopicSubtables,
    parseSubtopicTable,
    topicSubtables,
)
from dartlab.providers.dart.docs.sectionsLegacy.pipeline import sections
from dartlab.providers.dart.docs.sectionsLegacy.sectionsBase import (
    displayPeriod,
    formatPeriodRange,
    periodColumns,
    rawPeriod,
    reorderPeriodColumns,
    sortPeriods,
)
from dartlab.providers.dart.docs.sectionsLegacy.types import (
    SectionChunk,
    SectionResult,
    YearSections,
)
from dartlab.providers.dart.docs.sectionsLegacy.views import (
    buildMarkdownBlocks,
    buildMarkdownWide,
    contextSlices,
    retrievalBlocks,
)

__all__ = [
    "sections",
    "projectFreqRows",
    "structureRegistry",
    "structureCollisions",
    "structureEvents",
    "structureSummary",
    "structureChanges",
    "semanticRegistry",
    "semanticCollisions",
    "retrievalBlocks",
    "contextSlices",
    "buildMarkdownBlocks",
    "buildMarkdownWide",
    "topicSubtables",
    "TopicSubtables",
    "parseSubtopicTable",
    "ParsedSubtopicTable",
    "sortPeriods",
    "rawPeriod",
    "displayPeriod",
    "periodColumns",
    "formatPeriodRange",
    "reorderPeriodColumns",
    "SectionChunk",
    "SectionResult",
    "YearSections",
]
