"""graph.json 자동 빌드 — Skill Graph 분석 산출물 SSOT.

Description
-----------
6 JSON 산출물 중 *graph.json 만* 자동 빌드 결. 나머지 5 종 (index/agent/mcp/web/
pyodide) 은 운영자 수동 작성 SSOT (feedback_no_skill_json_auto_build 메모리).

graph.json 은 *분석·검증 결과* — `dartlab.skills.graph.buildSkillGraph()` 의
nodes + edges + cycles + entry + orphan + unreachable 직렬화. 사람이 손으로
다듬을 결 아님 — spec 의 frontmatter 관계 그래프가 SSOT.

빌드 결:
- nodes: 257 (skill id × title × degree × cluster × isEntry/isLeaf/isOrphan)
- edges: ~1337 (successor · linkedRecipe · knowledge · source 4 종)
- cycles: 3+ 노드 SCC
- entryNodes / unreachableFromEntry / orphanNodes

사용법:
    uv run python -X utf8 scripts/build/buildSkillGraph.py
    uv run python -X utf8 scripts/build/buildSkillGraph.py --check    # diff only, no write
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH_JSON = ROOT / "src" / "dartlab" / "skills" / "graph.json"


def _toPayload(graph) -> dict:
    """SkillGraph dataclass → JSON-직렬화 가능 dict.

    Description
    -----------
    landing `GraphPayload` interface 호환 schema (`landing/src/lib/skills/graphData.ts`):
    `entries` / `cycles` / `orphans` / `unreachable` (dataclass field name 그대로 직렬화
    하지 않음 — SkillGraph 의 entryNodes/orphanNodes/unreachableFromEntry 를 landing
    호환 이름으로 매핑). audiences 는 tuple → list.
    """
    nodes = []
    for n in graph.nodes:
        d = asdict(n)
        d["audiences"] = list(d.get("audiences", []))
        nodes.append(d)
    edges = [asdict(e) for e in graph.edges]
    return {
        "nodes": nodes,
        "edges": edges,
        "entries": list(graph.entryNodes),
        "cycles": [list(c) for c in graph.cycles],
        "orphans": list(graph.orphanNodes),
        "unreachable": list(graph.unreachableFromEntry),
    }


def main() -> int:
    """graph.json 빌드 — listSkills() 로드 + buildSkillGraph() + JSON dump."""
    parser = argparse.ArgumentParser(description="graph.json 자동 빌드")
    parser.add_argument(
        "--check",
        action="store_true",
        help="기존 graph.json 과 diff 만 출력 (write 안 함). CI 정합성 검증용.",
    )
    args = parser.parse_args()

    # lazy import — dartlab 로드 비용 분리.
    from dartlab.skills.graph import buildSkillGraph
    from dartlab.skills.registry import listSkills

    specs = listSkills(includeUser=False)
    graph = buildSkillGraph(specs)
    payload = _toPayload(graph)
    new_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        if not GRAPH_JSON.exists():
            print(f"[check] {GRAPH_JSON.relative_to(ROOT)} 없음 — 새 빌드 필요", file=sys.stderr)
            return 1
        existing = GRAPH_JSON.read_text(encoding="utf-8")
        if existing == new_text:
            print(
                f"[check] {GRAPH_JSON.relative_to(ROOT)} 일치 (nodes={len(payload['nodes'])} edges={len(payload['edges'])})"
            )
            return 0
        print(
            f"[check] {GRAPH_JSON.relative_to(ROOT)} 불일치 — 빌드 필요 "
            f"(nodes={len(payload['nodes'])} edges={len(payload['edges'])})",
            file=sys.stderr,
        )
        return 1

    GRAPH_JSON.write_text(new_text, encoding="utf-8")
    print(
        f"[ok] {GRAPH_JSON.relative_to(ROOT)} "
        f"nodes={len(payload['nodes'])} edges={len(payload['edges'])} "
        f"cycles={len(payload['cycles'])} orphans={len(payload['orphans'])} "
        f"unreachable={len(payload['unreachable'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
