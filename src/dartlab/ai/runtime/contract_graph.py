"""Compatibility shim for the generated Analysis Graph.

Runtime contract lookup now lives in :mod:`dartlab.core.analysisGraph` so AI
runtime and MCP clients read the same graph.
"""

from __future__ import annotations

from dartlab.core.analysisGraph import (
    CapabilityContract,
    PreflightAction,
    QuestionProfile,
    allContracts,
    allProcessMaps,
    answerContractNames,
    contractForTool,
    contractIdsForQuestion,
    contractsForQuestion,
    explainDartlabTool,
    graphStatus,
    inferQuestionProfile,
    listDartlabProcesses,
    planDartlabQuestion,
    preflightActionsForQuestion,
    processMapsForQuestion,
    requiresVisualExplanation,
    routeQuestion,
    toolBudgetForQuestion,
    toolNamesForQuestion,
    understandingPacketForQuestion,
    validateDartlabPlan,
)

legacyAnswerContractNames = answerContractNames

__all__ = [
    "CapabilityContract",
    "PreflightAction",
    "QuestionProfile",
    "allContracts",
    "allProcessMaps",
    "answerContractNames",
    "contractForTool",
    "contractIdsForQuestion",
    "contractsForQuestion",
    "explainDartlabTool",
    "graphStatus",
    "inferQuestionProfile",
    "listDartlabProcesses",
    "legacyAnswerContractNames",
    "planDartlabQuestion",
    "preflightActionsForQuestion",
    "processMapsForQuestion",
    "requiresVisualExplanation",
    "routeQuestion",
    "toolBudgetForQuestion",
    "toolNamesForQuestion",
    "understandingPacketForQuestion",
    "validateDartlabPlan",
]
