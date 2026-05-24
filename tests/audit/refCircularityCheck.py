"""ref circularity audit — DFS 순환 감지 (T11-3).

워크벤치 5 패스 trace 의 ref 호출 그래프에서 *순환* (A → B → A) 감지.
입력: `ai/trace.py::AuditCollector.dumpToJson` 결과 (T11-4).

순환 정의:
    같은 호출 chain 안에서 ref ID 가 두 번 이상 등장 — 무한 루프 위험.

탐지 패턴:
    1. event.data.refUsed 와 event.data.refProduced 의 ID 가 DFS 경로 안 중복
    2. tool call 의 입력 ref 가 같은 chain 의 출력 ref 와 동일

실행::

    uv run python -X utf8 tests/audit/refCircularityCheck.py
    uv run python -X utf8 tests/audit/refCircularityCheck.py \
        --trace data/_trace/{session}.json
    uv run python -X utf8 tests/audit/refCircularityCheck.py --strict

종료 코드:
    0 — 순환 0
    2 — --strict + 순환 ≥ 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TRACE_DIR = REPO_ROOT / "data" / "_trace"


def loadTrace(filePath: Path) -> dict:
    return json.loads(filePath.read_text(encoding="utf-8"))


def detectCircularRefs(events: list[dict]) -> list[dict]:
    """events 안 ref 의존 그래프에서 순환 chain 검출.

    각 event 는 형식:
        {
            "kind": "<BRIEF|WORK|...>",
            "data": {
                "refUsed": [<id>, ...],   # 본 step 이 입력으로 받은 ref 들
                "refProduced": "<id>",     # 본 step 이 발급한 새 ref
                ...
            },
            "at": "...",
        }

    DFS 로 ref → ref 의존 그래프 구축 후 cycle 감지.
    """
    # 그래프: producedRef → 사용한 (입력) refs
    graph: dict[str, set[str]] = {}
    for ev in events:
        data = ev.get("data", {})
        produced = data.get("refProduced")
        used = data.get("refUsed", [])
        if not produced:
            continue
        graph.setdefault(produced, set()).update(used or [])

    # DFS cycle detection (Tarjan-style 단순화 — node 별 WHITE/GRAY/BLACK).
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    cycles: list[dict] = []

    def dfs(node: str, path: list[str]) -> None:
        if color.get(node, WHITE) == GRAY:
            # cycle 발견 — path 안 node 부터 끝까지
            cycleStart = path.index(node)
            cycleNodes = path[cycleStart:] + [node]
            cycles.append({"nodes": cycleNodes, "length": len(cycleNodes) - 1})
            return
        if color.get(node, WHITE) == BLACK:
            return
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, set()):
            dfs(neighbor, path)
        path.pop()
        color[node] = BLACK

    for node in list(graph.keys()):
        if color.get(node, WHITE) == WHITE:
            dfs(node, [])

    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(description="ref circularity audit (T11-3)")
    parser.add_argument(
        "--trace",
        default=None,
        help="단일 trace JSON 파일. 미지정 시 data/_trace/ 전체 스캔.",
    )
    parser.add_argument("--strict", action="store_true", help="순환 1 이상 시 exit 2")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    tracePaths: list[Path]
    if args.trace:
        tracePaths = [Path(args.trace)]
    elif DEFAULT_TRACE_DIR.is_dir():
        tracePaths = sorted(DEFAULT_TRACE_DIR.glob("*.json"))
    else:
        tracePaths = []

    if not tracePaths:
        print("[refCircularity] 분석할 trace 0건 — data/_trace/ 또는 --trace 명시")
        return 0

    results: dict[str, list[dict]] = {}
    for tracePath in tracePaths:
        try:
            trace = loadTrace(tracePath)
        except (json.JSONDecodeError, OSError):
            continue
        events = trace.get("events", [])
        cycles = detectCircularRefs(events)
        if cycles:
            results[str(tracePath.relative_to(REPO_ROOT))] = cycles

    if args.json:
        print(json.dumps({"scanned": len(tracePaths), "withCycles": results}, ensure_ascii=False, indent=2))
    else:
        print(f"[refCircularity] 스캔 {len(tracePaths)} trace")
        if not results:
            print("[refCircularity] OK — 순환 0")
        else:
            print(f"[refCircularity] 순환 검출 — {len(results)} trace 안 {sum(len(v) for v in results.values())} cycle")
            for path, cycles in list(results.items())[:5]:
                print(f"  - {path}: {len(cycles)} cycle")
                for cyc in cycles[:3]:
                    nodes = " → ".join(cyc["nodes"][:5])
                    print(f"      길이 {cyc['length']}: {nodes}")

    if args.strict and results:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
