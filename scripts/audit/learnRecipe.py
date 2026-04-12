"""수동 recipe 학습 — 검증된 코드 패턴을 playbook에 저장.

사용법::

    uv run python -X utf8 scripts/audit/learnRecipe.py "매출 증가 회사" "df = dartlab.scan('growth'); print(df.sort('매출CAGR', descending=True).head(20))"
    uv run python -X utf8 scripts/audit/learnRecipe.py --batch seed.json
    uv run python -X utf8 scripts/audit/learnRecipe.py --list

저장된 recipe는 KnowledgeDB playbook 테이블에 source="recipe"로 저장.
HF push 시 자동 공유. 사용자 auto_pull로 자동 다운로드.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def learn_one(question: str, code: str, *, intent: str | None = None) -> bool:
    """단일 recipe 학습."""
    from dartlab.ai.context.intent import classifyIntent
    from dartlab.ai.persistence.knowledge_db import KnowledgeDB

    if intent is None:
        result = classifyIntent(question, hasCompany=False)
        intent = result.intent.value

    bullet = f"{question[:80]} → {code[:500]}"

    db = KnowledgeDB.get()
    db.upsert_bullet(
        intent=intent,
        sector="",
        bullet=bullet,
        outcome="success",
        source="recipe",
    )
    print(f"  저장: [{intent}] {question[:40]}... → {code[:60]}...")
    return True


def learn_batch(path: Path) -> int:
    """JSON 파일에서 배치 학습.

    JSON 형식::

        [
            {"question": "매출 증가 회사", "code": "df = dartlab.scan('growth')..."},
            {"question": "경기 사이클", "code": "print(dartlab.macro('사이클'))"},
            ...
        ]
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    for item in data:
        q = item["question"]
        c = item["code"]
        intent = item.get("intent")
        if learn_one(q, c, intent=intent):
            count += 1
    return count


def list_recipes() -> None:
    """저장된 recipe 목록 출력."""
    from dartlab.ai.persistence.knowledge_db import KnowledgeDB

    db = KnowledgeDB.get()
    conn = db._ensure_db()
    rows = conn.execute(
        "SELECT intent, bullet, success_count, quality FROM playbook WHERE source = 'recipe' ORDER BY quality DESC"
    ).fetchall()

    if not rows:
        print("저장된 recipe 없음")
        return

    print(f"총 {len(rows)}개 recipe:\n")
    for intent, bullet, sc, quality in rows:
        print(f"[{intent:15s}] (quality={quality:.2f}, used={sc}) {bullet[:100]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="dartlab AI recipe 수동 학습")
    parser.add_argument("question", nargs="?", help="질문 패턴")
    parser.add_argument("code", nargs="?", help="성공 코드")
    parser.add_argument("--intent", help="intent 강제 지정")
    parser.add_argument("--batch", help="JSON 파일에서 배치 학습")
    parser.add_argument("--list", action="store_true", help="저장된 recipe 목록")
    args = parser.parse_args()

    if args.list:
        list_recipes()
        return 0

    if args.batch:
        count = learn_batch(Path(args.batch))
        print(f"\n{count}개 recipe 학습 완료")
        return 0

    if args.question and args.code:
        learn_one(args.question, args.code, intent=args.intent)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
