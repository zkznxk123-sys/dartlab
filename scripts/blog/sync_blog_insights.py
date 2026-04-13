"""블로그 frontmatter ai: 블록 → KnowledgeDB insights(source="blog") 파생.

블로그 마크다운이 source of truth. 이 스크립트가 ai: 블록을 읽어서
KnowledgeDB에 자동 저장. GitHub Actions(하루 1회) 또는 수동 실행.

사용법::

    uv run python -X utf8 scripts/blog/sync_blog_insights.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_BLOG_DIR = Path("blog/05-company-reports")


def _parse_frontmatter(text: str) -> dict:
    """마크다운에서 YAML frontmatter를 간이 파싱."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}

    fm_text = parts[1]
    result: dict = {}

    for line in fm_text.strip().split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^(\w[\w\s]*?):\s*"?(.+?)"?\s*$', line)
        if m:
            result[m.group(1).strip()] = m.group(2).strip().strip('"')

    return result


def _parse_ai_block(text: str) -> dict | None:
    """frontmatter에서 ai: 블록을 추출."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None

    fm = parts[1]
    if "ai:" not in fm:
        return None

    ai_section = fm[fm.index("ai:") :]
    result: dict = {}

    for line in ai_section.split("\n"):
        line = line.strip()
        if not line or line == "ai:":
            continue

        # verdict, direction 등 단순 키
        m = re.match(r'^(\w+):\s*"?(.+?)"?\s*$', line)
        if m:
            key, val = m.group(1), m.group(2)
            if key in ("verdict", "direction", "confidence", "archetype", "dataAsOf"):
                result[key] = val.strip('"')

        # strengths/weaknesses 리스트 아이템
        if line.startswith('- "') or line.startswith("- "):
            val = line.lstrip("- ").strip('"')
            if "strengths" in result and isinstance(result.get("_last_list"), str) and result["_last_list"] == "strengths":
                result.setdefault("strengths", []).append(val)
            elif "weaknesses" in result and isinstance(result.get("_last_list"), str) and result["_last_list"] == "weaknesses":
                result.setdefault("weaknesses", []).append(val)

        if line == "strengths:":
            result["_last_list"] = "strengths"
            result["strengths"] = []
        elif line == "weaknesses:":
            result["_last_list"] = "weaknesses"
            result["weaknesses"] = []

    result.pop("_last_list", None)
    return result if result.get("verdict") else None


def sync() -> int:
    """모든 블로그 포스트의 ai: 블록을 KnowledgeDB에 저장."""
    try:
        from dartlab.ai.persistence.knowledge_db import KnowledgeDB
    except ImportError:
        print("dartlab 패키지를 찾을 수 없습니다.")
        return 1

    db = KnowledgeDB.get()
    count = 0

    for post_dir in sorted(_BLOG_DIR.iterdir()):
        index_md = post_dir / "index.md"
        if not index_md.exists():
            continue

        text = index_md.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        ai = _parse_ai_block(text)

        if not ai or not fm.get("stockCode"):
            continue

        stock_code = fm["stockCode"]
        sector = fm.get("sector", "")
        verdict = ai.get("verdict", "")
        direction = ai.get("direction", "")
        confidence = ai.get("confidence", "")

        narrative = f"[{direction}/{confidence}] {verdict}"
        strengths = ai.get("strengths", [])
        weaknesses = ai.get("weaknesses", [])

        db.save_insight(
            stock_code=stock_code,
            narrative=narrative,
            strengths=strengths,
            weaknesses=weaknesses,
            sector=sector,
            source="blog",
            expires_days=365,
        )
        count += 1
        print(f"  {post_dir.name} → insights(source=blog)")

    print(f"\n총 {count}개 blog insight 저장 완료.")
    return 0


if __name__ == "__main__":
    sys.exit(sync())
