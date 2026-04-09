"""core/graph — 기업 재무 인과 그래프 (Phase 2).

FINOS ai-evals-framework + Microsoft GraphRAG 패턴.
14축 calc 결과를 노드/엣지로 모델링하여 인과 질문에 환각 없이 답한다.

진입점:
    from dartlab.analysis.graph import CompanyGraph, buildGraph
    g = buildGraph(company)
    causes = g.causes("영업이익률")  # 마진 하락 원인 트리
"""

from dartlab.analysis.graph.schema import CompanyGraph, Edge, EdgeType, Node, NodeType
from dartlab.analysis.graph.builder import buildGraph
from dartlab.analysis.graph.traverse import causes, ancestors, timeline, related

__all__ = [
    "CompanyGraph",
    "Edge",
    "EdgeType",
    "Node",
    "NodeType",
    "buildGraph",
    "causes",
    "ancestors",
    "timeline",
    "related",
]
