"""orphan 분류 후보 리포트 — Skill Graph 의 orphan 노드 자동 분류 hint.

Description
-----------
Skill Graph phase 1 warn-only 가 orphan 카운트만 출력하지만 분류는 운영자
손작업. 본 스크립트는 graph.json 의 isOrphan=true 노드 전부를 카테고리별로
묶고, 자동 분류 가능한 후보 (자연 leaf 결) 를 `isLeafNode: true` 마킹 추천,
그 외 misclassification 후보는 connect 권고.

분류 휴리스틱:
- category=runtime · operation: 일반적으로 leaf (참조 받기만 하는 운영 룰).
- category=engines: in/out 모두 0 = 의도치 않은 misclassification 후보 ↑.
- category=start: leaf 아닌 entry — orphan 이면 entryHint 또는 후속 successor 추가 권고.
- procedure 비어있고 본문 짧음 = isLeafNode 후보.

출력:
- stdout 표 (category × 추천 액션).
- `scripts/audit/_baselines/skillGraphOrphans.json` — 분류 결과 JSON.

사용법:
    uv run python -X utf8 scripts/audit/skillGraphOrphanReport.py
    uv run python -X utf8 scripts/audit/skillGraphOrphanReport.py --json-only
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRAPH_JSON = ROOT / "src" / "dartlab" / "skills" / "graph.json"
BASELINE = ROOT / "scripts" / "audit" / "_baselines" / "skillGraphOrphans.json"


def classify(node: dict) -> str:
    """orphan 노드에 대한 자동 분류 액션 추정.

    Description
    -----------
    isOrphan=true 정의는 "inDegree=0 + isEntry=false + isLeafNode=false". 즉 누구도
    참조하지 않는 진입 미달 노드. 분류는 in/out degree 조합으로:

    - in=0 + out=0: 완전 격리. 운영자 검토 필요 (review).
    - in=0 + out>0: head 결 — entry 진입 안 되지만 다른 skill 참조 함.
      `entryHint: true` 마킹 또는 누가 본 노드를 `successors` 로 가리키게 권고.
    - in>0 + out=0: 자연 leaf — `isLeafNode: true` 안전 (단, isOrphan 정의상 in=0 이라
      이 경우는 거의 안 일어남).

    Returns
    -------
    str
        "isolated" — in=0 + out=0, 운영자 검토.
        "head-needs-entry" — in=0 + out>0, entryHint 또는 incoming successor 추가.
        "true-leaf" — in>0 + out=0, isLeafNode: true 안전 마킹.
        "review" — 분류 불가.
    """
    in_deg = node.get("inDegree", 0)
    out_deg = node.get("outDegree", 0)
    if in_deg == 0 and out_deg == 0:
        return "isolated"
    if in_deg == 0 and out_deg > 0:
        return "head-needs-entry"
    if in_deg > 0 and out_deg == 0:
        return "true-leaf"
    return "review"


def main() -> int:
    """orphan 리포트 빌드 + 분류 후보 출력."""
    parser = argparse.ArgumentParser(description="Skill Graph orphan 분류 리포트")
    parser.add_argument("--json-only", action="store_true", help="stdout 표 출력 생략, JSON 만 갱신")
    args = parser.parse_args()

    if not GRAPH_JSON.exists():
        print(
            f"[error] {GRAPH_JSON} 없음. Skill OS 산출물을 먼저 명시적으로 관리하라.",
            file=sys.stderr,
        )
        return 1

    data = json.loads(GRAPH_JSON.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    orphans = [n for n in nodes if n.get("isOrphan")]

    grouped: dict[str, list[dict]] = defaultdict(list)
    for node in orphans:
        action = classify(node)
        grouped[action].append(
            {
                "id": node["id"],
                "category": node.get("category", ""),
                "inDegree": node.get("inDegree", 0),
                "outDegree": node.get("outDegree", 0),
                "title": node.get("title", ""),
            }
        )

    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(
        json.dumps(
            {
                "totalOrphans": len(orphans),
                "byAction": {action: len(items) for action, items in grouped.items()},
                "candidates": grouped,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.json_only:
        print(f"[ok] {BASELINE.relative_to(ROOT)} 갱신 ({len(orphans)} orphans)")
        return 0

    print(f"orphan 총 {len(orphans)} 개 — 카테고리별 분류 후보\n")
    actions_desc = {
        "isolated": "→ 완전 격리 (in=0 + out=0). 운영자 검토 필수",
        "head-needs-entry": "→ entry 미진입 (in=0 + out>0). entryHint: true 또는 incoming successor 추가",
        "true-leaf": "→ 자연 leaf (in>0 + out=0). isLeafNode: true 안전 마킹",
        "review": "→ 휴리스틱 판정 불가 — 운영자 수동 검토",
    }
    for action, items in sorted(grouped.items()):
        desc = actions_desc.get(action, "")
        print(f"\n[{action}] {len(items)} 건 {desc}")
        for item in sorted(items, key=lambda x: x["id"])[:20]:
            print(f"  - {item['id']:<55} ({item['category']:<10}) in={item['inDegree']} out={item['outDegree']}")
        if len(items) > 20:
            print(f"  ... +{len(items) - 20} 더 (전체는 {BASELINE.relative_to(ROOT)})")

    print(f"\n전체 결과: {BASELINE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
