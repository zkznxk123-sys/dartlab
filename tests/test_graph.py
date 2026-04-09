"""core/graph Phase 2 단위 테스트.

scope:
- schema: Node/Edge/CompanyGraph CRUD + findNodes
- builder: buildGraph (실제 Company — integration 마커)
- traverse: causes/ancestors/timeline/related + narrative
- selector: selectGraphCauses (인과 질문 → ContextPart)
"""

from __future__ import annotations

import pytest

from dartlab.core.graph.schema import (
    CompanyGraph,
    Edge,
    EdgeType,
    Node,
    NodeType,
)
from dartlab.core.graph.traverse import (
    ancestors,
    causes,
    causesNarrative,
    related,
    timeline,
    timelineNarrative,
)

pytestmark = pytest.mark.unit


# ── schema ────────────────────────────────────────────────


class TestSchema:
    def test_node_creation(self):
        n = Node(id="metric:ROE:2024", type=NodeType.METRIC, label="ROE", value=12.5, period="2024", unit="%")
        assert n.label == "ROE"
        assert n.value == 12.5

    def test_graph_add_node_edge(self):
        g = CompanyGraph("005930", "삼성전자")
        g.addNode(Node(id="a", type=NodeType.METRIC, label="A"))
        g.addNode(Node(id="b", type=NodeType.METRIC, label="B"))
        g.addEdge(Edge(source="a", target="b", type=EdgeType.CAUSES))
        assert len(g) == 2
        assert g.edgeCount() == 1

    def test_incoming_outgoing(self):
        g = CompanyGraph()
        g.addNode(Node(id="a", type=NodeType.METRIC, label="A"))
        g.addNode(Node(id="b", type=NodeType.METRIC, label="B"))
        g.addEdge(Edge(source="a", target="b", type=EdgeType.CAUSES))
        assert len(g.outgoing("a")) == 1
        assert len(g.incoming("b")) == 1
        assert g.outgoing("a")[0].target == "b"
        assert g.incoming("b")[0].source == "a"

    def test_find_nodes(self):
        g = CompanyGraph()
        g.addNode(Node(id="1", type=NodeType.METRIC, label="영업이익률", period="2024"))
        g.addNode(Node(id="2", type=NodeType.SEGMENT, label="DX"))
        assert len(g.findNodes(type=NodeType.METRIC)) == 1
        assert len(g.findNodes(label="영업")) == 1
        assert len(g.findNodes(label="DX")) == 1


# ── traverse ──────────────────────────────────────────────


def _buildTestGraph() -> CompanyGraph:
    """테스트용 3계층 인과 그래프.
    매출 → 영업이익률 → 순이익률
    DX부문 --partOf--> 매출
    Z-Score --anomaly--> Z-Score
    """
    g = CompanyGraph("005930", "삼성전자")
    g.addNode(Node("metric:매출:2024", NodeType.METRIC, "매출", 100, "2024", "조"))
    g.addNode(Node("metric:매출:2023", NodeType.METRIC, "매출", 90, "2023", "조"))
    g.addNode(Node("metric:영업이익률:2024", NodeType.METRIC, "영업이익률", 13.1, "2024", "%"))
    g.addNode(Node("metric:순이익률:2024", NodeType.METRIC, "순이익률", 10.2, "2024", "%"))
    g.addNode(Node("segment:DX", NodeType.SEGMENT, "DX", 51))
    g.addNode(Node("metric:Z-Score:2024", NodeType.METRIC, "Z-Score", 1.5, "2024"))

    g.addEdge(Edge("metric:매출:2024", "metric:영업이익률:2024", EdgeType.CAUSES, label="매출 규모 → 마진"))
    g.addEdge(Edge("metric:영업이익률:2024", "metric:순이익률:2024", EdgeType.CAUSES, label="영업이익 → 순이익"))
    g.addEdge(Edge("segment:DX", "metric:매출:2024", EdgeType.PART_OF, label="51%"))
    g.addEdge(Edge("metric:Z-Score:2024", "metric:Z-Score:2024", EdgeType.ANOMALY, label="Z-Score 1.5 < 1.8"))
    return g


class TestTraverse:
    def test_causes_depth1(self):
        g = _buildTestGraph()
        result = causes(g, "영업이익률", max_depth=1)
        assert len(result) >= 1
        assert any(n.label == "매출" for n, e, d in result)

    def test_causes_depth2(self):
        g = _buildTestGraph()
        result = causes(g, "순이익률", max_depth=2)
        labels = {n.label for n, e, d in result}
        assert "영업이익률" in labels
        assert "매출" in labels

    def test_ancestors_partof(self):
        g = _buildTestGraph()
        result = ancestors(g, "매출")
        assert any(n.label == "DX" for n in result)

    def test_timeline(self):
        g = _buildTestGraph()
        result = timeline(g, "매출")
        assert len(result) == 2
        assert result[0].period == "2023"
        assert result[1].period == "2024"

    def test_related(self):
        g = _buildTestGraph()
        result = related(g, "영업이익률")
        labels = {n.label for n, e in result}
        assert "매출" in labels or "순이익률" in labels

    def test_causes_narrative(self):
        g = _buildTestGraph()
        text = causesNarrative(g, "순이익률")
        assert "영업이익률" in text
        assert "매출" in text

    def test_timeline_narrative(self):
        g = _buildTestGraph()
        text = timelineNarrative(g, "매출")
        assert "2023" in text
        assert "2024" in text
        assert "상승" in text

    def test_empty_label(self):
        g = _buildTestGraph()
        result = causes(g, "없는지표")
        assert result == []


# ── selector ──────────────────────────────────────────────


class _FakeCompany:
    stockCode = "005930"
    corpName = "삼성전자"
    sector = "반도체"


class TestGraphSelector:
    def test_non_why_question_returns_nothing(self):
        from dartlab.ai.context.selectors.graph import selectGraphCauses

        parts = selectGraphCauses("영업이익률 추세", _FakeCompany())
        assert parts == []

    def test_no_company_returns_nothing(self):
        from dartlab.ai.context.selectors.graph import selectGraphCauses

        parts = selectGraphCauses("왜 마진이 떨어졌나", None)
        assert parts == []
