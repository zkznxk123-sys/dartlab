"""사업보고서 섹션 구조화 모듈."""

from dartlab.providers.dart.docs.sectionsArchive.analysis import (
    projectFreqRows,
    semanticCollisions,
    semanticRegistry,
    structureChanges,
    structureCollisions,
    structureEvents,
    structureRegistry,
    structureSummary,
)
from dartlab.providers.dart.docs.sectionsArchive.extractors import (
    ParsedSubtopicTable,
    TopicSubtables,
    parseSubtopicTable,
    topicSubtables,
)
from dartlab.providers.dart.docs.sectionsArchive.pipeline import sections
from dartlab.providers.dart.docs.sectionsArchive.sectionsBase import (
    displayPeriod,
    formatPeriodRange,
    periodColumns,
    rawPeriod,
    reorderPeriodColumns,
    sortPeriods,
)
from dartlab.providers.dart.docs.sectionsArchive.types import (
    SectionChunk,
    SectionResult,
    YearSections,
)
from dartlab.providers.dart.docs.sectionsArchive.views import (
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
