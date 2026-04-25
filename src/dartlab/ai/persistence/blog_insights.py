"""블로그 frontmatter `ai:` 블록 → `KnowledgeDB.insights(source="blog")` 다리.

사상 (ops/philosophy.md §6): 사람이 만든 블로그 서사가 자동으로 AI 자산이 되는
경로 1. 기존 `pastInsight(stockCode)` 가 `source="blog"` 우선 조회하지만
변환 경로가 없어 레코드 0 건이었음 — 이 파일이 그 끊김을 복구한다.

진입점
=======

- `upsert_ai_frontmatter_to_insights(post_path)` — 단일 블로그 포스트 변환
- `backfill_all(blog_root)` — 다수 포스트 일괄 (백필용)

호출 지점
=========

- publisher 직후 (실시간 훅) — `src/dartlab/story/publisher.py`
- 일괄 백필 — `scripts/audit/backfill_blog_insights.py`
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """`---` 블록 frontmatter 파싱. 없으면 빈 dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = text[3:end].strip()
    try:
        import yaml

        data = yaml.safe_load(fm_block) or {}
    except (ImportError, Exception):  # noqa: BLE001
        # yaml 없거나 파싱 실패 (escape 문자 등) 시 매우 단순 파싱 (top-level key: value 만)
        data = {}
        for line in fm_block.splitlines():
            if ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                data[k.strip()] = v.strip().strip("\"'")
    return data if isinstance(data, dict) else {}


def upsert_ai_frontmatter_to_insights(post_path: Path) -> bool:
    """frontmatter `ai:` + `stockCode` 있는 포스트를 `insights(source="blog")` 로.

    반환: True 변환 성공, False 스킵 (ai 블록 없음 · stockCode 없음).
    """
    fm = _parse_frontmatter(Path(post_path))
    if not fm:
        return False
    ai = fm.get("ai")
    stock_code = fm.get("stockCode") or fm.get("stock_code")
    if not ai or not isinstance(ai, dict) or not stock_code:
        return False

    narrative = str(ai.get("verdict") or ai.get("narrative") or "")[:500]
    strengths = json.dumps(ai.get("strengths", []) or [], ensure_ascii=False)
    weaknesses = json.dumps(ai.get("weaknesses", []) or [], ensure_ascii=False)
    key_metrics = json.dumps(ai.get("keyMetrics") or ai.get("key_metrics") or {}, ensure_ascii=False)
    sector = fm.get("sector") or ""
    data_as_of = str(ai.get("dataAsOf") or ai.get("data_as_of") or "")

    try:
        from dartlab.ai.persistence.knowledge_db import _get_db

        db = _get_db()
    except Exception:
        return False

    conn = getattr(db, "_conn", None)
    if conn is None:
        return False

    try:
        # 컬럼 존재 여부 확인 + 없으면 ALTER (migration v3)
        cursor = conn.execute("PRAGMA table_info(insights)")
        cols = {row[1] for row in cursor.fetchall()}
        if "data_as_of" not in cols:
            conn.execute("ALTER TABLE insights ADD COLUMN data_as_of TEXT")
        if "key_metrics" not in cols:
            conn.execute("ALTER TABLE insights ADD COLUMN key_metrics TEXT")
        if "evidence_ref" not in cols:
            conn.execute("ALTER TABLE insights ADD COLUMN evidence_ref TEXT")
        if "quality_gate" not in cols:
            conn.execute("ALTER TABLE insights ADD COLUMN quality_gate TEXT")

        now = time.time()
        expires = now + 365 * 86400
        evidence = f"blog:{Path(post_path).as_posix()}"
        conn.execute(
            """INSERT OR REPLACE INTO insights
               (stock_code, narrative, strengths, weaknesses, key_metrics, sector,
                source, created_at, expires_at, data_as_of, evidence_ref, quality_gate)
               VALUES (?, ?, ?, ?, ?, ?, 'blog', ?, ?, ?, ?, 'human-approved')""",
            (stock_code, narrative, strengths, weaknesses, key_metrics, sector, now, expires, data_as_of, evidence),
        )
        conn.commit()
        return True
    except Exception:
        return False


def backfill_all(blog_root: Path, glob: str = "**/index.md") -> tuple[int, int]:
    """블로그 루트 순회 → 일괄 변환.

    반환: (변환 성공 수, 스킵 수)
    """
    ok = 0
    skipped = 0
    for md in Path(blog_root).glob(glob):
        if upsert_ai_frontmatter_to_insights(md):
            ok += 1
        else:
            skipped += 1
    return ok, skipped


__all__ = ["upsert_ai_frontmatter_to_insights", "backfill_all"]
