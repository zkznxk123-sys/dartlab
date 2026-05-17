"""그래프 탐색 쿼리 — causes/ancestors/timeline/related.

인과 질문 ("왜 마진이 떨어졌나") → 그래프 traversal → 텍스트 결과.
모든 주장이 노드 ID로 추적 가능 → 환각 0.
"""

from __future__ import annotations

from dartlab.analysis.graph.schema import CompanyGraph, Edge, EdgeType, Node


def causes(
    graph: CompanyGraph,
    label: str,
    *,
    maxDepth: int = 3,
) -> list[tuple[Node, Edge, int]]:
    """label 매칭 노드의 원인 트리 (역방향 BFS).

    Capabilities:
        - "왜 X 가 발생했나" 역추적 → 원인 노드 + 엣지 + depth 평탄화 리스트.

    Guide:
        findNodes(label) → graph.incoming() BFS, maxDepth 까지 확장.

    When:
        인과 질문 ("매출 하락 원인") → graph 기반 무환각 답변 시.

    How:
        visited set 으로 사이클 방지. BFS (pop(0)) 폭우선.

    Requires:
        graph 가 CompanyGraph 인스턴스이며 findNodes/incoming/getNode 지원.

    Raises:
        없음. 매칭 노드 0 개 시 빈 리스트.

    Parameters:
        graph : CompanyGraph
            탐색 대상 그래프.
        label : str
            검색할 노드 라벨 (부분 매칭).
        max_depth : int
            최대 탐색 깊이 (기본 3).

    Returns:
        list[tuple[Node, Edge, int]]
            (원인노드, 엣지, depth) 튜플 리스트. depth 1이 직접 원인.

    Example:
        >>> causes(graph, "영업이익률")
        [(Node(label="원자재가격"), Edge(...), 1), ...]

    See Also:
        - causesNarrative : 본 함수 결과를 markdown 서사로 변환.

    AIContext:
        depth=1 직접 원인을 우선 인용, depth>1 은 추가 맥락.
    """
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    results: list[tuple[Node, Edge, int]] = []
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(t.id, 0) for t in targets]

    while queue:
        nid, depth = queue.pop(0)
        if depth >= maxDepth:
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
    maxDepth: int = 5,
) -> list[Node]:
    """label 매칭 노드의 조상 체인 (PART_OF 엣지만).

    Capabilities:
        - PART_OF 관계만 추적해 계층 구조 (사업부 → 회사 → 그룹) 조상 노드 반환.

    Guide:
        BFS 로 incoming PART_OF 엣지만 따라가며 결과 노드 누적.

    When:
        지표가 속한 상위 계층 (제품 → 사업부 → 회사 → 섹터) 확인 시.

    How:
        edge.type != PART_OF skip. visited 로 중복 방지.

    Requires:
        graph 의 edge 가 EdgeType.PART_OF 종류 보유.

    Raises:
        없음.

    Parameters:
        graph : CompanyGraph
            탐색 대상 그래프.
        label : str
            검색할 노드 라벨 (부분 매칭).
        max_depth : int
            최대 조상 수 (기본 5).

    Returns:
        list[Node]
            PART_OF 관계의 조상 노드 리스트.

    Example:
        >>> ancestors(graph, "갤럭시")
        [Node(label="MX 사업부"), Node(label="삼성전자")]

    See Also:
        - related : 모든 엣지 타입 양방향 연결 노드.

    AIContext:
        지표를 상위 계층 관점으로 재해석할 때 인용.
    """
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    result: list[Node] = []
    visited: set[str] = set()
    queue = [t.id for t in targets]

    while queue:
        nid = queue.pop(0)
        if len(result) >= maxDepth:
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
    """같은 label의 노드를 기간순 정렬.

    Requires:
        그래프 내 동일 label 노드들이 node.period 속성을 가짐.

    Raises:
        없음.

    Example:
        >>> timeline(graph, "영업이익률")
        [Node(period="2022"), Node(period="2023"), Node(period="2024")]

    Parameters:
        graph : CompanyGraph
            탐색 대상 그래프.
        label : str
            검색할 노드 라벨 (부분 매칭).

    Returns:
        list[Node]
            period 오름차순 정렬된 노드 리스트.
    """
    nodes = graph.findNodes(label=label)
    return sorted(nodes, key=lambda n: n.period)


def related(
    graph: CompanyGraph,
    label: str,
    *,
    edgeType: EdgeType | None = None,
) -> list[tuple[Node, Edge]]:
    """label 매칭 노드의 연결된 노드 (forward + backward).

    Capabilities:
        - 양방향 (outgoing + incoming) 1-hop 이웃 노드 반환.

    Guide:
        edgeType 필터 옵션. None 시 모든 타입 통과.

    When:
        주변 노드 한 번에 탐색 (ego network) 시.

    How:
        outgoing → target, incoming → source 수집. seen set 으로 중복 제거.

    Requires:
        graph 의 outgoing/incoming 헬퍼.

    Raises:
        없음.

    Parameters:
        graph : CompanyGraph
            탐색 대상 그래프.
        label : str
            검색할 노드 라벨 (부분 매칭).
        edge_type : EdgeType, optional
            필터링할 엣지 타입. None이면 전체.

    Returns:
        list[tuple[Node, Edge]]
            (연결 노드, 엣지) 튜플 리스트 (중복 제거).

    Example:
        >>> related(graph, "영업이익률", edgeType=EdgeType.CAUSES)
        [(Node(...), Edge(type=CAUSES)), ...]

    See Also:
        - causes : 인과만 역방향 탐색.

    AIContext:
        한 지표의 직접 이웃 (원인/결과/부분) 한 번에 보고 인용.
    """
    targets = graph.findNodes(label=label)
    if not targets:
        return []

    results: list[tuple[Node, Edge]] = []
    seen: set[str] = set()

    for t in targets:
        for edge in graph.outgoing(t.id):
            if edgeType and edge.type != edgeType:
                continue
            if edge.target not in seen:
                node = graph.getNode(edge.target)
                if node:
                    results.append((node, edge))
                    seen.add(edge.target)
        for edge in graph.incoming(t.id):
            if edgeType and edge.type != edgeType:
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

    Capabilities:
        - causes 트리 → markdown indent + "←" 화살표 서사.

    Guide:
        depth 가 깊을수록 indent 증가. 노드 value/period/edge label 포함.

    When:
        AI 답변 본문에 직접 인용 가능한 인과 텍스트 필요 시.

    How:
        causes(graph, label) → 각 row 를 indent + "← {label}{val}{period}" 포맷.

    Requires:
        graph 가 cause 추적 가능 (CompanyGraph + edge 데이터).

    Raises:
        없음. 원인 없으면 안내 문자열.

    Parameters:
        graph : CompanyGraph
            탐색 대상 그래프.
        label : str
            원인 분석할 노드 라벨.

    Returns:
        str
            마크다운 원인 분석 서사. 원인 없으면 안내 메시지.

    Example:
        >>> print(causesNarrative(graph, "영업이익률"))
        ### 영업이익률 원인 분석
          ← 원자재가격 = 100USD/bbl (2024Q4) — 상승

    See Also:
        - causes : raw 결과 함수.

    AIContext:
        무환각 인과 서사. 본문 그대로 인용 가능.
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
    """timeline() 결과를 추이 서사로.

    Capabilities:
        - timeline 정렬 → markdown bullet + 상승/하락/보합 판정.

    Guide:
        period 별 값 bullet. 처음/마지막 비교로 추세 단어 결정.

    When:
        시계열 변화 자연어 설명 필요 시.

    How:
        vals[-1] vs vals[0] 비교. 같으면 보합.

    Requires:
        graph + label 노드들이 period 기준 정렬 가능.

    Raises:
        없음. 데이터 없으면 안내 문자열.

    Parameters:
        graph : CompanyGraph
            대상 그래프.
        label : str
            추적할 지표 라벨.

    Returns:
        str
            추이 서사 마크다운 텍스트. 데이터 없으면 안내 문구.

    Example:
        >>> print(timelineNarrative(graph, "영업이익률"))
        ### 영업이익률 추이
        - 2022: 10%
        - 2023: 12%

    See Also:
        - timeline : raw 정렬 결과.

    AIContext:
        시계열 답변 본문에 직접 인용.
    """
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
            lines.append("\n→ **보합**")

    return "\n".join(lines)
