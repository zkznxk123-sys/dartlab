"""KnowledgeDB 오염 정리 — W-D2 재설계.

기존 insights/playbook/executions 에 검증 게이트 없이 쌓인 오염 레코드를
정리하고, source 엄격 구분 + 품질 게이트 + evidence_ref 가 있는 새 스키마로
재출발한다.

정리 대상
========

- `insights(source="live")` → **전량 drop** (post-response 무조건 저장, 검증 없음)
- `insights(source="audit")` → auditAnalysis md 실제 존재하는 것만 이관
- `insights(source="blog")` → 0 건 (W-D backfill 로 채워짐)
- `playbook` → `quality >= 0.75 AND success_count >= 5` 만 유지 (노이즈 prune)
- `executions` → `question` → `question_hash` 로 치환. 최근 30 일만 유지

새 스키마 컬럼 (insights)
========================

- `evidence_ref` — 원본 추적 (blog:path, audit:path, live:request_id)
- `quality_gate` — human-approved · auto-extracted · migration

사용
====

dry-run (기본)
    uv run python scripts/audit/cleanup_knowledge_db.py

실행
    uv run python scripts/audit/cleanup_knowledge_db.py --confirm
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _find_db() -> Path | None:
    """KnowledgeDB 파일 경로 추정."""
    candidates = [
        Path.home() / ".dartlab" / "dartlab_knowledge.db",
        ROOT / "data" / "ai" / "knowledge" / "dartlab_knowledge.db",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _archive(db_path: Path) -> Path:
    """cleanup 전 스냅샷."""
    archive_dir = ROOT / "data" / "ai" / "knowledge" / "_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dst = archive_dir / f"{today}-pre-cleanup.sqlite"
    shutil.copy2(db_path, dst)
    return dst


def _ensure_columns(conn: sqlite3.Connection) -> None:
    """migration v3 — insights 테이블 컬럼 확장."""
    cur = conn.execute("PRAGMA table_info(insights)")
    cols = {row[1] for row in cur.fetchall()}
    if "evidence_ref" not in cols:
        conn.execute("ALTER TABLE insights ADD COLUMN evidence_ref TEXT")
    if "quality_gate" not in cols:
        conn.execute("ALTER TABLE insights ADD COLUMN quality_gate TEXT")
    if "data_as_of" not in cols:
        conn.execute("ALTER TABLE insights ADD COLUMN data_as_of TEXT")
    if "key_metrics" not in cols:
        conn.execute("ALTER TABLE insights ADD COLUMN key_metrics TEXT")
    conn.commit()


def _dry_run_report(conn: sqlite3.Connection, audit_dir: Path) -> dict:
    """정리 영향 카운트만 보고."""
    report = {}

    # insights by source
    cur = conn.execute("SELECT source, COUNT(*) FROM insights GROUP BY source")
    report["insights_by_source"] = dict(cur.fetchall())

    # audit md 실제 존재하는 종목 수
    valid_audit_stocks = set()
    if audit_dir.is_dir():
        valid_audit_stocks = {p.stem for p in audit_dir.glob("*.md")}
    cur = conn.execute("SELECT DISTINCT stock_code FROM insights WHERE source = 'audit'")
    audit_stocks = {row[0] for row in cur.fetchall()}
    report["audit_stocks_orphan"] = len(audit_stocks - valid_audit_stocks)
    report["audit_stocks_valid"] = len(audit_stocks & valid_audit_stocks)

    # playbook low-quality
    cur = conn.execute("SELECT COUNT(*) FROM playbook WHERE NOT (quality >= 0.75 AND success_count >= 5)")
    report["playbook_to_prune"] = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM playbook WHERE quality >= 0.75 AND success_count >= 5")
    report["playbook_keep"] = cur.fetchone()[0]

    # executions 오래된 것
    cutoff = time.time() - 30 * 86400
    cur = conn.execute("SELECT COUNT(*) FROM executions WHERE created_at < ?", (cutoff,))
    report["executions_to_drop"] = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(*) FROM executions WHERE created_at >= ?", (cutoff,))
    report["executions_keep"] = cur.fetchone()[0]

    return report


def _cleanup(conn: sqlite3.Connection, audit_dir: Path) -> dict:
    """실제 정리 실행."""
    stats = {"drop_live": 0, "drop_orphan_audit": 0, "prune_playbook": 0, "drop_old_exec": 0}

    # 1. live 전량 drop
    cur = conn.execute("DELETE FROM insights WHERE source = 'live'")
    stats["drop_live"] = cur.rowcount

    # 2. audit source 중 md 실제 존재 안 하는 것 drop
    valid_audit = set()
    if audit_dir.is_dir():
        valid_audit = {p.stem for p in audit_dir.glob("*.md")}
    cur = conn.execute("SELECT id, stock_code FROM insights WHERE source = 'audit'")
    orphans = [row[0] for row in cur.fetchall() if row[1] not in valid_audit]
    if orphans:
        placeholders = ",".join("?" for _ in orphans)
        conn.execute(f"DELETE FROM insights WHERE id IN ({placeholders})", orphans)
        stats["drop_orphan_audit"] = len(orphans)

    # 3. 남은 audit 레코드에 evidence_ref · quality_gate 주입
    conn.execute(
        "UPDATE insights SET evidence_ref = 'audit:data/dart/auditAnalysis/' || stock_code || '.md', "
        "quality_gate = 'migration' "
        "WHERE source = 'audit' AND (evidence_ref IS NULL OR evidence_ref = '')"
    )

    # 4. playbook prune
    cur = conn.execute("DELETE FROM playbook WHERE NOT (quality >= 0.75 AND success_count >= 5)")
    stats["prune_playbook"] = cur.rowcount

    # 5. executions 30 일 이전 drop + question 원문 해시화
    cutoff = time.time() - 30 * 86400
    cur = conn.execute("DELETE FROM executions WHERE created_at < ?", (cutoff,))
    stats["drop_old_exec"] = cur.rowcount

    # executions.question → hash (최근 30 일 남은 것)
    # 기존 컬럼이 NOT NULL 이면 별도 컬럼 추가. 여기선 단순화: 기존 question 을 해시로 덮어씀
    import hashlib

    cur = conn.execute("SELECT id, question FROM executions WHERE question IS NOT NULL")
    for row in cur.fetchall():
        q = row[1] or ""
        if not q.startswith("sha256:"):
            h = "sha256:" + hashlib.sha256(q.encode("utf-8")).hexdigest()[:16]
            conn.execute("UPDATE executions SET question = ? WHERE id = ?", (h, row[0]))

    conn.commit()
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=None, help="KnowledgeDB 경로 (자동 탐색)")
    ap.add_argument("--audit-dir", type=Path, default=ROOT / "data" / "dart" / "auditAnalysis")
    ap.add_argument("--confirm", action="store_true", help="실제 정리. 없으면 dry-run 리포트만")
    args = ap.parse_args()

    db_path = args.db or _find_db()
    if db_path is None or not db_path.is_file():
        print("[info] KnowledgeDB 미생성 — 정리할 것 없음.")
        return 0

    conn = sqlite3.connect(db_path)
    try:
        _ensure_columns(conn)

        if not args.confirm:
            report = _dry_run_report(conn, args.audit_dir)
            print(f"[dry-run] DB: {db_path}")
            print(f"  insights by source: {report['insights_by_source']}")
            print(f"  audit 레코드: valid {report['audit_stocks_valid']} / orphan {report['audit_stocks_orphan']}")
            print(f"  playbook: keep {report['playbook_keep']} / prune {report['playbook_to_prune']}")
            print(f"  executions: keep {report['executions_keep']} / drop {report['executions_to_drop']} (30일 이전)")
            print("\n  실행: --confirm 추가")
            return 0

        # 아카이브
        archive = _archive(db_path)
        print(f"[archive] {archive.relative_to(ROOT) if archive.is_relative_to(ROOT) else archive}")

        # 정리
        stats = _cleanup(conn, args.audit_dir)
        log_path = ROOT / "data" / "ai" / "knowledge" / "_cleanup.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {stats}\n")

        print("[cleanup] 완료:")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print(f"\n  아카이브: {archive}")
        print(f"  로그: {log_path.relative_to(ROOT)}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
