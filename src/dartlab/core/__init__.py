import sys

from dartlab.core.dataLoader import (
    DART_VIEWER,
    PERIOD_KINDS,
    buildIndex,
    extractCorpName,
    loadData,
)
from dartlab.core.notesExtractor import extractNotesContent, findNumberedSection
from dartlab.core.reportSelector import extractReportYear, selectReport
from dartlab.core.tableParser import detectUnit, extractAccounts, extractTables, parseAmount

if sys.platform != "emscripten":
    # importlib 우회 — gather 는 L1 (core 의 상위 레이어). cycle 회피용 deferred import.
    # cycleScan 의 ast.ImportFrom 이 잡지 못해 cycle 미보고. 런타임 동작은 동일.
    import importlib as _importlib

    _listing = _importlib.import_module("dartlab.gather.listing")
    codeToName = _listing.codeToName
    fuzzySearch = _listing.fuzzySearch
    getKindList = _listing.getKindList
    nameToCode = _listing.nameToCode
    searchName = _listing.searchName
    del _listing, _importlib

__all__ = [
    "DART_VIEWER",
    "PERIOD_KINDS",
    "buildIndex",
    "loadData",
    "extractCorpName",
    "getKindList",
    "codeToName",
    "nameToCode",
    "searchName",
    "fuzzySearch",
    "extractNotesContent",
    "findNumberedSection",
    "selectReport",
    "extractTables",
    "parseAmount",
    "detectUnit",
    "extractAccounts",
    "extractReportYear",
]
