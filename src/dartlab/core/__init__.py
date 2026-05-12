"""core layer 진입점 — L0 primitive 만 노출.

L1 listing 함수 (codeToName/fuzzySearch/...) 는 dartlab/__init__.py 가 직접
re-export 하므로 core 가 노출 책임 짊어지지 않음 (정공법 D — Facade).
"""

from dartlab.core.dataLoader import (
    DART_VIEWER,
    PERIOD_KINDS,
    buildIndex,
    extractCorpName,
    loadData,
)
from dartlab.providers.notesExtractor import extractNotesContent, findNumberedSection
from dartlab.providers.reportSelector import extractReportYear, selectReport
from dartlab.providers.tableParser import detectUnit, extractAccounts, extractTables, parseAmount

__all__ = [
    "DART_VIEWER",
    "PERIOD_KINDS",
    "buildIndex",
    "loadData",
    "extractCorpName",
    "extractNotesContent",
    "findNumberedSection",
    "selectReport",
    "extractTables",
    "parseAmount",
    "detectUnit",
    "extractAccounts",
    "extractReportYear",
]
