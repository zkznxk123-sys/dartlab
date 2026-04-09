"""그래프 탐색 쿼리 — causes/ancestors/timeline/related.

인과 질문 ("왜 마진이 떨어졌나") → 그래프 traversal → 텍스트 결과.
모든 주장이 노드 ID로 추적 가능 → 환각 0.
"""

from __future__ import annotations

from dartlab.analysis.graph.schema import CompanyGraph, Edge, EdgeType, Node, NodeType


def causes(
    graph: CompanyGraph,
    label: str,
    *,
    max_depth: int = 3,
) -> list[tuple[Node, Edge, int]]:
    """label 매칭 노드의 원인 트리 (역방향 BFS).

    Returns:
        [(원인노드, 엣지, depth), ...] — depth 1이 직접 원인.
    """
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    results: list[tuple[Node, Edge, int]] = []
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(t.id, 0) for t in targets]

    while queue:
        nid, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for edge in graph.incoming(nid):
            if edge.source in visited:
                continue
            visited.add(edge.source)
            source_node = graph.getNode(edge.source)
            if source_node:
                results.append((source_node, edge, depth + 1))
                queue.append((edge.source, depth + 1))

    return results


def ancestors(
    graph: CompanyGraph,
    label: str,
    *,
    max_depth: int = 5,
) -> list[Node]:
    """label 매칭 노드의 조상 체인 (PART_OF 엣지만)."""
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    result: list[Node] = []
    visited: set[str] = set()
    queue = [t.id for t in targets]

    while queue:
        nid = queue.pop(0)
        if len(result) >= max_depth:
            break
        for edge in graph.incoming(nid):
            if edge.type != EdgeType.PART_OF:
                continue
            if edge.source in visited:
                continue
            visited.add(edge.source)
            node = graph.getNode(edge.source)
            if node:
                result.append(node)
                queue.append(edge.source)

    return result


def timeline(
    graph: CompanyGraph,
    label: str,
) -> list[Node]:
    """같은 label의 노드를 기간순 정렬."""
    nodes = graph.findNodes(label=label)
    return sorted(nodes, key=lambda n: n.period)


def related(
    graph: CompanyGraph,
    label: str,
    *,
    edge_type: EdgeType | None = None,
) -> list[tuple[Node, Edge]]:
    """label 매칭 노드의 연결된 노드 (forward + backward)."""
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    results: list[tuple[Node, Edge]] = []
    seen: set[str] = set()

    for t in targets:
        for edge in graph.outgoing(t.id):
            if edge_type and edge.type != edge_type:
                continue
            if edge.target not in seen:
                node = graph.getNode(edge.target)
                if node:
                    results.append((node, edge))
                    seen.add(edge.target)
        for edge in graph.incoming(t.id):
            if edge_type and edge.type != edge_type:
                continue
            if edge.source not in seen:
                node = graph.getNode(edge.source)
                if node:
                    results.append((node, edge))
                    seen.add(edge.source)

    return results


# ── 서사 생성 ─────────────────────────────────────────────


def causesNarrative(graph: CompanyGraph, label: str) -> str:
    """causes() 결과를 자연어 서사로 변환.

    환각 0 보장: 모든 문장이 노드 value + edge label에서 생성됨.
    """
    chain = causes(graph, label)
    if not chain:
        return f"'{label}'에 대한 원인 관계를 찾을 수 없습니다."

    lines = [f"### {label} 원인 분석"]
    for node, edge, depth in chain:
        indent = "  " * depth
        val = f" = {node.value}{node.unit}" if node.value is not None else ""
        period = f" ({node.period})" if node.period else ""
        edge_label = f" — {edge.label}" if edge.label else ""
        lines.append(f"{indent}← {node.label}{val}{period}{edge_label}")

    return "\n".join(lines)


def timelineNarrative(graph: CompanyGraph, label: str) -> str:
    """timeline() 결과를 추이 서사로."""
    nodes = timeline(graph, label)
    if not nodes:
        return f"'{label}' 시계열 데이터 없음."

    lines = [f"### {label} 추이"]
    for n in nodes:
        val = f"{n.value}{n.unit}" if n.value is not None else "N/A"
        lines.append(f"- {n.period}: {val}")

    # 방향 판단
    vals = [n.value for n in nodes if isinstance(n.value, (int, float))]
    if len(vals) >= 2:
        if vals[-1] > vals[0]:
            lines.append(f"\n→ **상승 추세** ({vals[0]} → {vals[-1]})")
        elif vals[-1] < vals[0]:
            lines.append(f"\n→ **하락 추세** ({vals[0]} → {vals[-1]})")
        else:
            lines.append(f"\n→ **보합**")

    return "\n".join(lines)
