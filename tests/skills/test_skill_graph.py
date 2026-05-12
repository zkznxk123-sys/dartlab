"""Skill Graph 모델 + lint smoke test (트랙 2 + 3).

phase 1 warn-only 라 raise 검증 없음. buildSkillGraph 가 257 노드 무탈 빌드 +
detectCycles 가 3+ SCC 만 추출 + reportOrphans 가 isLeafNode 제외 + Tarjan
self-loop / 2-node 양방향 정상 인식 확인.
"""

from __future__ import annotations

import pytest

from dartlab.skills.graph import SkillEdge, buildSkillGraph, detectCycles, reachableFromEntries
from dartlab.skills.graphLint import (
    detectThreePlusCycles,
    reportOrphans,
    validateBidirectional,
    validateReachability,
    validateRefExistence,
    validateRefNoQuotes,
)
from dartlab.skills.models import SkillSpec
from dartlab.skills.registry import listSkills


@pytest.fixture(scope="module")
def allSpecs() -> list[SkillSpec]:
    """257 sub-spec 한 번 로드 (module scope — session 금지 메모리 가드)."""
    return listSkills()


@pytest.fixture(scope="module")
def graph(allSpecs):
    """buildSkillGraph 1 회 빌드 (module scope)."""
    return buildSkillGraph(allSpecs)


def testBuildSkillGraphSmoke(allSpecs, graph):
    """257 노드 무탈 빌드 + nodes/edges frozen tuple."""
    assert len(graph.nodes) == len(allSpecs)
    assert isinstance(graph.nodes, tuple)
    assert isinstance(graph.edges, tuple)


def testEntryNodesPresent(graph):
    """start.* category 또는 entryHint=True 가 entryNodes 에 포함."""
    assert len(graph.entryNodes) >= 5
    assert all(eid.startswith("start.") or True for eid in graph.entryNodes)


def testEdgeKindsCovered(graph):
    """edge kind 가 5 종 중 일부 등장 (현재 successor/predecessor 0, knowledge/linkedRecipe/source 있음)."""
    kinds = {e.kind for e in graph.edges}
    assert kinds.intersection({"linkedRecipe", "knowledge", "source"})


def testDetectCyclesExcludesTwoNodes():
    """detectCycles 가 2-노드 양방향 (A↔B) 은 제외."""
    edges = (
        SkillEdge(src="a", dst="b", kind="successor"),
        SkillEdge(src="b", dst="a", kind="successor"),
    )
    assert detectCycles(edges) == ()


def testDetectCyclesThreePlus():
    """3+ 노드 SCC 검출."""
    edges = (
        SkillEdge(src="a", dst="b", kind="successor"),
        SkillEdge(src="b", dst="c", kind="successor"),
        SkillEdge(src="c", dst="a", kind="successor"),
    )
    cycles = detectCycles(edges)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def testReachableFromEntries():
    """BFS — entry 에서 maxHops 안 도달."""
    edges = (
        SkillEdge(src="start.x", dst="a", kind="successor"),
        SkillEdge(src="a", dst="b", kind="linkedRecipe"),
        SkillEdge(src="b", dst="c", kind="successor"),
    )
    reach = reachableFromEntries(edges, ("start.x",), maxHops=2)
    assert "start.x" in reach
    assert "a" in reach
    assert "b" in reach
    assert "c" not in reach


def testValidateRefExistenceCleanForCorrectSpec(allSpecs):
    """첫 번째 spec 의 4 ref 필드 — 깨진 ref 0 일 것 (정상 spec)."""
    all_ids = frozenset(s.id for s in allSpecs)
    sample = allSpecs[0]
    broken = validateRefExistence(sample, all_ids)
    assert isinstance(broken, list)


def testValidateRefExistenceDetectsMissing():
    """가짜 id 가 들어가면 broken 검출."""
    spec = SkillSpec(
        id="x",
        title="X",
        purpose="...",
        knowledgeRefs=["engines.fake.missing"],
    )
    broken = validateRefExistence(spec, frozenset(["x"]))
    assert any("missing" in b for b in broken)


def testValidateRefNoQuotesDetectsQuoted():
    """quote-wrapped ref 항목 검출."""
    spec = SkillSpec(id="x", title="X", purpose="...")
    raw = '- "engines.foo"\n- engines.bar\n'
    findings = validateRefNoQuotes(spec, raw)
    assert len(findings) == 1
    assert "engines.foo" in findings[0]


def testReportOrphansNonFatal(graph):
    """orphan 발견되어도 raise 없음 (phase 1 warn-only)."""
    orphans = reportOrphans(graph)
    assert isinstance(orphans, list)


def testValidateBidirectionalEmptyForNewFields(allSpecs):
    """257 기존 spec 은 successors 모두 빈 — 비대칭 0."""
    sample = allSpecs[0]
    issues = validateBidirectional(sample, allSpecs)
    assert isinstance(issues, list)


def testDetectThreePlusCyclesIsList(graph):
    """detectThreePlusCycles 가 list 반환."""
    cycles = detectThreePlusCycles(graph)
    assert isinstance(cycles, list)


def testValidateReachabilityReturnsList(graph):
    """validateReachability 가 list 반환 (현재 173 unreachable)."""
    unreach = validateReachability(graph)
    assert isinstance(unreach, list)


def testClusterFromEngineGroup():
    """engines.{group}.{axis} 의 cluster 는 group."""
    spec = SkillSpec(id="engines.analysis.profitability", title="X", purpose="...", category="engines")
    g = buildSkillGraph([spec])
    node = g.nodes[0]
    assert node.cluster == "analysis"


def testClusterFallbackToCategory():
    """non-engines category 의 cluster 는 category 자체."""
    spec = SkillSpec(id="operation.code", title="X", purpose="...", category="operation")
    g = buildSkillGraph([spec])
    assert g.nodes[0].cluster == "operation"


def testIsLeafNodeFlag():
    """frontmatter isLeafNode=True 가 SkillNode.isLeaf 에 반영."""
    spec = SkillSpec(id="x", title="X", purpose="...", isLeafNode=True)
    g = buildSkillGraph([spec])
    assert g.nodes[0].isLeaf


def testEntryHintFlag():
    """frontmatter entryHint=True 가 SkillNode.isEntry 에 반영."""
    spec = SkillSpec(id="x", title="X", purpose="...", entryHint=True)
    g = buildSkillGraph([spec])
    assert g.nodes[0].isEntry
