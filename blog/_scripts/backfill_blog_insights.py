"""블로그 frontmatter `ai:` 블록 → insights(source="blog") 일괄 백필.

사용
====

dry-run (기본)
    uv run python blog/_scripts/backfill_blog_insights.py --blog-root blog/ --dry-run

실행
    uv run python blog/_scripts/backfill_blog_insights.py --blog-root blog/ --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blog-root", type=Path, default=ROOT / "blog")
    ap.add_argument("--glob", default="**/index.md")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--confirm", action="store_true", help="실제 KnowledgeDB 쓰기")
    args = ap.parse_args()

    if not args.blog_root.is_dir():
        print(f"[fatal] blog-root 없음: {args.blog_root}")
        return 1

    if not args.confirm:
        # dry-run: 후보 개수만 카운트
        from dartlab.ai.persistence.blog_insights import _parse_frontmatter

        with_ai = 0
        total = 0
        for md in args.blog_root.glob(args.glob):
            total += 1
            fm = _parse_frontmatter(md)
            if fm.get("ai") and (fm.get("stockCode") or fm.get("stock_code")):
                with_ai += 1
        print(f"[dry-run] 전체 {total} 포스트 · ai-block 보유 {with_ai} 건")
        print("  실행: --confirm 추가")
        return 0

    from dartlab.ai.persistence.blog_insights import backfill_all

    ok, skipped = backfill_all(args.blog_root, glob=args.glob)
    print(f"[backfill] 성공 {ok} · 스킵 {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
