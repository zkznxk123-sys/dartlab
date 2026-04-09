"""KnowledgeDB - dartlab AI의 자기성장형 영속성 단일 DB.

5개 분산 저장소(analysisMemory.db, skill_library.db, error_patterns.db,
audit_log.jsonl, auditAnalysis/*.md)를 하나의 SQLite DB로 통합한다.

DB 위치: ~/.dartlab/ai_knowledge.db

핵심 테이블:
- executions: 모든 AI 실행 기록 (질문, 결과, 등급, 메트릭)
- skills: 성공한 코드 패턴 (few-shot 라이브러리)
- error_patterns: 에러 패턴 + 복구 코드
- insights: 기업별 심층 분석 서사 (auditAnalysis에서 축적)
- meta: DB 버전/마이그레이션 상태
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".dartlab" / "dartlab_knowledge.db"
_LEGACY_DB_PATH = Path.home() / ".dartlab" / "ai_knowledge.db"
_MIGRATION_VERSION = 1
_MAX_INSIGHT_NARRATIVE = 2000
_MAX_SUMMARY_CHARS = 500

# ── 싱글턴 ─────────────────────────────────────────────────

_instance: KnowledgeDB | None = None


# ── 데이터 클래스 ──────────────────────────────────────────


@dataclass(frozen=True)
class InsightRecord:
    """기업별 인사이트."""

    stock_code: str
    narrative: str
    strengths: list[str]
    weaknesses: list[str]
    sector: str
    source: str
    created_at: float
    expires_at: float | None


# ── 스키마 ─────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    question TEXT NOT NULL,
    question_type TEXT DEFAULT '',
    mode TEXT DEFAULT 'analysis',
    result_summary TEXT DEFAULT '',
    grade TEXT DEFAULT '',
    key_metrics TEXT DEFAULT '',
    duration_sec REAL,
    code_rounds INTEGER DEFAULT 0,
    has_error INTEGER DEFAULT 0,
    provider TEXT DEFAULT '',
    model TEXT DEFAULT '',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_exec_stock ON executions(stock_code);
CREATE INDEX IF NOT EXISTS idx_exec_mode ON executions(mode);
CREATE INDEX IF NOT EXISTS idx_exec_ts ON executions(created_at);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    tools_used TEXT NOT NULL DEFAULT '[]',
    code_template TEXT NOT NULL,
    result_keys TEXT NOT NULL DEFAULT '[]',
    success_count INTEGER NOT NULL DEFAULT 1,
    quality_score REAL NOT NULL DEFAULT 0.8,
    mode TEXT DEFAULT 'analysis',
    created_at REAL NOT NULL,
    last_used REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_skill_cat ON skills(category);
CREATE INDEX IF NOT EXISTS idx_skill_mode ON skills(mode);

CREATE TABLE IF NOT EXISTS error_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_type TEXT NOT NULL,
    error_signature TEXT NOT NULL,
    wrong_code TEXT NOT NULL DEFAULT '',
    correct_code TEXT NOT NULL DEFAULT '',
    tool_name TEXT NOT NULL DEFAULT '',
    frequency INTEGER NOT NULL DEFAULT 1,
    last_seen REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ep_sig ON error_patterns(error_signature);
CREATE INDEX IF NOT EXISTS idx_ep_tool ON error_patterns(tool_name);

CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT NOT NULL,
    narrative TEXT NOT NULL,
    strengths TEXT DEFAULT '[]',
    weaknesses TEXT DEFAULT '[]',
    sector TEXT DEFAULT '',
    source TEXT DEFAULT 'audit',
    created_at REAL NOT NULL,
    expires_at REAL
);
CREATE INDEX IF NOT EXISTS idx_ins_stock ON insights(stock_code);
CREATE INDEX IF NOT EXISTS idx_ins_sector ON insights(sector);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ACE (Agentic Context Engineering) playbook 테이블
-- arxiv.org/abs/2510.04618 — Generator/Reflector/Curator 폐쇄 루프
-- delta merge: 신규 bullet INSERT, 중복은 success/fail 카운트만 갱신 (삭제 금지 — context collapse 방지)
CREATE TABLE IF NOT EXISTS playbook (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent TEXT NOT NULL,
    sector TEXT NOT NULL DEFAULT '',
    bullet TEXT NOT NULL,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count INTEGER NOT NULL DEFAULT 0,
    quality REAL NOT NULL DEFAULT 0.5,
    source TEXT NOT NULL DEFAULT 'reflection',
    created_at REAL NOT NULL,
    last_used REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pb_intent ON playbook(intent);
CREATE INDEX IF NOT EXISTS idx_pb_quality ON playbook(quality DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pb_unique ON playbook(intent, sector, bullet);
"""


# ── KnowledgeDB ────────────────────────────────────────────


class KnowledgeDB:
    """dartlab AI 단일 영속성 DB."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._conn: sqlite3.Connection | None = None
        # 멀티스레드 write 직렬화 (P1-1 ThreadPoolExecutor 호환)
        # WAL + check_same_thread=False 면 read 는 동시 가능, write 만 lock 필요.
        self._write_lock = threading.RLock()

    # ── 연결 관리 ──────────────────────────────────────────

    def _ensure_db(self) -> sqlite3.Connection:
        """lazy init.

        check_same_thread=False — P1-1 백그라운드 thread 에서도 같은 connection
        사용 가능. WAL 모드라 read 는 동시 안전, write 는 _write_lock 으로 직렬화.
        """
        if self._conn is not None:
            return self._conn

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        # 기존 ai_knowledge.db → dartlab_knowledge.db 자동 rename
        if not self._db_path.exists() and _LEGACY_DB_PATH.exists():
            try:
                _LEGACY_DB_PATH.rename(self._db_path)
                log.info("DB rename: %s → %s", _LEGACY_DB_PATH.name, self._db_path.name)
            except OSError:
                pass  # rename 실패 시 새로 생성

        conn = sqlite3.connect(
            str(self._db_path),
            timeout=5,
            check_same_thread=False,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        self._conn = conn
        return conn

    @property
    def connection(self) -> sqlite3.Connection:
        """기존 모듈이 connection 직접 접근할 때 사용."""
        return self._ensure_db()

    def close(self) -> None:
        """SQLite 연결 닫기. 싱글톤 재초기화 시 호출."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── executions ─────────────────────────────────────────

    def save_execution(
        self,
        stock_code: str | None,
        question: str,
        *,
        question_type: str = "",
        mode: str = "analysis",
        result_summary: str = "",
        grade: str = "",
        key_metrics: str = "",
        duration_sec: float | None = None,
        code_rounds: int = 0,
        has_error: bool = False,
        provider: str = "",
        model: str = "",
    ) -> None:
        """AI 실행 1건을 ``executions`` 테이블에 기록.

        Args:
            stock_code: 종목코드 (없으면 None — market-level 질문).
            question: 사용자 질문 (200자로 절단).
            question_type: 질문 분류 ("analysis"/"compare"/"forecast" 등).
            mode: "analysis" | "coding".
            result_summary: 답변 요약 (_MAX_SUMMARY_CHARS 자로 절단).
            grade: 분석 결과 등급 (있으면).
            key_metrics: JSON 문자열 형태의 핵심 지표 (500자로 절단).
            duration_sec: 실행 시간 (초).
            code_rounds: 코드 실행 round 수.
            has_error: 에러 발생 여부.
            provider: LLM provider 식별자.
            model: 모델 식별자.
        """
        conn = self._ensure_db()
        summary = result_summary[:_MAX_SUMMARY_CHARS] if result_summary else ""
        conn.execute(
            "INSERT INTO executions "
            "(stock_code, question, question_type, mode, result_summary, grade, "
            "key_metrics, duration_sec, code_rounds, has_error, provider, model, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                stock_code,
                question[:200],
                question_type,
                mode,
                summary,
                grade or "",
                key_metrics[:500] if key_metrics else "",
                duration_sec,
                code_rounds,
                int(has_error),
                provider,
                model,
                time.time(),
            ),
        )
        conn.commit()

    def recall_for_stock(
        self,
        stock_code: str,
        limit: int = 5,
        decay_days: int = 90,
    ) -> list[dict]:
        """특정 종목의 최근 AI 실행 이력을 시간 역순으로 반환.

        AI 가 같은 종목의 분석 컨텍스트를 회상할 때 사용. ``decay_days`` 이전
        기록은 자동 제외 (오래된 정보의 영향 차단).

        Args:
            stock_code: 종목코드.
            limit: 반환 건수 상한.
            decay_days: 회상 윈도우 (일). 기본 90일.

        Returns:
            ``[{stock_code, question, question_type, result_summary, timestamp,
            grade, key_metrics}, ...]`` — 최신 우선.
        """
        conn = self._ensure_db()
        cutoff = time.time() - (decay_days * 86400)
        rows = conn.execute(
            "SELECT stock_code, question, question_type, result_summary, "
            "created_at, grade, key_metrics "
            "FROM executions WHERE stock_code = ? AND created_at > ? "
            "ORDER BY created_at DESC LIMIT ?",
            (stock_code, cutoff, limit),
        ).fetchall()
        return [
            {
                "stock_code": r[0],
                "question": r[1],
                "question_type": r[2],
                "result_summary": r[3],
                "timestamp": r[4],
                "grade": r[5],
                "key_metrics": r[6],
            }
            for r in rows
        ]

    # ── skills ─────────────────────────────────────────────

    def save_skill(
        self,
        question: str,
        code_template: str,
        *,
        category: str = "general",
        tools_used: str = "[]",
        result_keys: str = "[]",
        quality_score: float = 0.8,
        mode: str = "analysis",
    ) -> int | None:
        """성공한 코드 패턴을 ``skills`` 테이블에 저장 (few-shot 학습 자료).

        Args:
            question: 원본 질문 (500자로 절단).
            code_template: 실행에 성공한 코드 (5000자로 절단).
            category: skill 분류 ("financial"/"docs"/"market" 등).
            tools_used: 사용한 도구 목록 JSON.
            result_keys: 결과 dict 의 키 목록 JSON.
            quality_score: 0.0~1.0 품질 점수 (높을수록 우수).
            mode: "analysis" | "coding".

        Returns:
            INSERT 된 row 의 id, 실패 시 None.
        """
        conn = self._ensure_db()
        now = time.time()
        cursor = conn.execute(
            "INSERT INTO skills "
            "(question, category, tools_used, code_template, result_keys, "
            "success_count, quality_score, mode, created_at, last_used) "
            "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
            (
                question[:500],
                category,
                tools_used,
                code_template[:5000],
                result_keys,
                quality_score,
                mode,
                now,
                now,
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def search_skills(
        self,
        category: str,
        *,
        limit: int = 2,
        mode: str | None = None,
    ) -> list[tuple]:
        """카테고리 별 상위 품질 skill 검색 (few-shot 주입용).

        category 매칭 우선, 부족하면 mode 전체에서 보충.
        품질 점수 / 성공 횟수 내림차순 정렬.

        Args:
            category: skill 분류 키.
            limit: 반환 건수.
            mode: "analysis" | "coding" 중 하나로 제한 (None = 둘 다).

        Returns:
            sqlite row 튜플 리스트. 컬럼 순서는 ``skills`` 테이블 schema 기준.
        """
        conn = self._ensure_db()
        if mode:
            rows = conn.execute(
                "SELECT * FROM skills WHERE category = ? AND mode = ? "
                "ORDER BY quality_score DESC, success_count DESC LIMIT ?",
                (category, mode, limit),
            ).fetchall()
            if len(rows) < limit:
                existing_ids = {r[0] for r in rows}
                extra = conn.execute(
                    "SELECT * FROM skills WHERE mode = ? ORDER BY quality_score DESC, success_count DESC LIMIT ?",
                    (mode, limit * 3),
                ).fetchall()
                for r in extra:
                    if r[0] not in existing_ids and len(rows) < limit:
                        rows.append(r)
        else:
            rows = conn.execute(
                "SELECT * FROM skills WHERE category = ? ORDER BY quality_score DESC, success_count DESC LIMIT ?",
                (category, limit),
            ).fetchall()
            if len(rows) < limit:
                existing_ids = {r[0] for r in rows}
                extra = conn.execute(
                    "SELECT * FROM skills ORDER BY quality_score DESC, success_count DESC LIMIT ?",
                    (limit * 3,),
                ).fetchall()
                for r in extra:
                    if r[0] not in existing_ids and len(rows) < limit:
                        rows.append(r)
        return rows

    def record_skill_success(self, skill_id: int) -> None:
        """skill 의 ``success_count`` 증가 + ``last_used`` 갱신.

        skill 을 재사용하여 성공할 때마다 호출 — 점진적 품질 신호.
        """
        conn = self._ensure_db()
        conn.execute(
            "UPDATE skills SET success_count = success_count + 1, last_used = ? WHERE id = ?",
            (time.time(), skill_id),
        )
        conn.commit()

    def adjust_skill_quality(self, skill_id: int, success: bool) -> None:
        """EMA 방식 품질 점수 업데이트."""
        alpha = 0.3
        conn = self._ensure_db()
        row = conn.execute("SELECT quality_score FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if row:
            current = row[0]
            new_score = current * (1 - alpha) + (1.0 if success else 0.0) * alpha
            conn.execute(
                "UPDATE skills SET quality_score = ?, last_used = ? WHERE id = ?",
                (new_score, time.time(), skill_id),
            )
            conn.commit()

    # ── error_patterns ─────────────────────────────────────

    def lookup_error(self, signature: str, error_type: str, *, limit: int = 3) -> list[tuple]:
        conn = self._ensure_db()
        rows = conn.execute(
            "SELECT * FROM error_patterns WHERE error_signature = ? ORDER BY frequency DESC LIMIT ?",
            (signature, limit),
        ).fetchall()
        if len(rows) < limit and error_type != "Unknown":
            existing_ids = {r[0] for r in rows}
            type_rows = conn.execute(
                "SELECT * FROM error_patterns WHERE error_type = ? ORDER BY frequency DESC LIMIT ?",
                (error_type, limit * 2),
            ).fetchall()
            for r in type_rows:
                if r[0] not in existing_ids and len(rows) < limit:
                    rows.append(r)
        return rows

    def record_error(
        self,
        error_type: str,
        signature: str,
        wrong_code: str,
        correct_code: str = "",
        tool_name: str = "",
    ) -> None:
        conn = self._ensure_db()
        now = time.time()
        existing = conn.execute(
            "SELECT id, frequency FROM error_patterns WHERE error_signature = ? AND wrong_code = ?",
            (signature, wrong_code[:2000]),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE error_patterns SET frequency = ?, last_seen = ?, "
                "correct_code = CASE WHEN ? != '' THEN ? ELSE correct_code END "
                "WHERE id = ?",
                (existing[1] + 1, now, correct_code, correct_code, existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO error_patterns "
                "(error_type, error_signature, wrong_code, correct_code, tool_name, frequency, last_seen) "
                "VALUES (?, ?, ?, ?, ?, 1, ?)",
                (error_type, signature, wrong_code[:2000], correct_code[:2000], tool_name, now),
            )
        conn.commit()

    # ── insights ───────────────────────────────────────────

    def save_insight(
        self,
        stock_code: str,
        narrative: str,
        *,
        strengths: list[str] | None = None,
        weaknesses: list[str] | None = None,
        sector: str = "",
        source: str = "audit",
        expires_days: int = 90,
    ) -> None:
        conn = self._ensure_db()
        now = time.time()
        expires_at = now + (expires_days * 86400)

        # upsert: 같은 종목 + source면 갱신
        existing = conn.execute(
            "SELECT id FROM insights WHERE stock_code = ? AND source = ?",
            (stock_code, source),
        ).fetchone()

        narrative_trimmed = narrative[:_MAX_INSIGHT_NARRATIVE]
        strengths_json = json.dumps(strengths or [], ensure_ascii=False)
        weaknesses_json = json.dumps(weaknesses or [], ensure_ascii=False)

        if existing:
            conn.execute(
                "UPDATE insights SET narrative = ?, strengths = ?, weaknesses = ?, "
                "sector = ?, created_at = ?, expires_at = ? WHERE id = ?",
                (narrative_trimmed, strengths_json, weaknesses_json, sector, now, expires_at, existing[0]),
            )
        else:
            conn.execute(
                "INSERT INTO insights "
                "(stock_code, narrative, strengths, weaknesses, sector, source, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (stock_code, narrative_trimmed, strengths_json, weaknesses_json, sector, source, now, expires_at),
            )
        conn.commit()

    def get_insight(self, stock_code: str) -> InsightRecord | None:
        conn = self._ensure_db()
        row = conn.execute(
            "SELECT stock_code, narrative, strengths, weaknesses, sector, source, "
            "created_at, expires_at FROM insights "
            "WHERE stock_code = ? ORDER BY created_at DESC LIMIT 1",
            (stock_code,),
        ).fetchone()
        if not row:
            return None
        return InsightRecord(
            stock_code=row[0],
            narrative=row[1],
            strengths=json.loads(row[2]) if row[2] else [],
            weaknesses=json.loads(row[3]) if row[3] else [],
            sector=row[4] or "",
            source=row[5] or "audit",
            created_at=row[6],
            expires_at=row[7],
        )

    def get_sector_insights(self, sector: str, *, limit: int = 3) -> list[InsightRecord]:
        conn = self._ensure_db()
        rows = conn.execute(
            "SELECT stock_code, narrative, strengths, weaknesses, sector, source, "
            "created_at, expires_at FROM insights "
            "WHERE sector LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{sector}%", limit),
        ).fetchall()
        return [
            InsightRecord(
                stock_code=r[0],
                narrative=r[1],
                strengths=json.loads(r[2]) if r[2] else [],
                weaknesses=json.loads(r[3]) if r[3] else [],
                sector=r[4] or "",
                source=r[5] or "audit",
                created_at=r[6],
                expires_at=r[7],
            )
            for r in rows
        ]

    # ── playbook (ACE: Generator/Reflector/Curator) ────────
    # arxiv.org/abs/2510.04618 — delta merge로 evolving playbook 유지.
    # 규칙: 신규 bullet INSERT, 중복은 카운트만 갱신, 절대 삭제 X (context collapse 방지).

    def upsert_bullet(
        self,
        intent: str,
        bullet: str,
        *,
        sector: str = "",
        outcome: str = "neutral",
        source: str = "reflection",
    ) -> None:
        """playbook bullet 삽입 또는 카운트 갱신.

        Args:
            intent: ai.context.intent.Intent.value (예: "act2_profit").
            bullet: 한 줄 전략/관찰 (200자 cap, 자동 절단).
            sector: 섹터 분리 (기본 빈 문자열 = 전 섹터 공용).
            outcome: "success" → success_count++, "fail" → fail_count++, "neutral" → 등록만.
            source: "reflection" | "audit" | "manual".

        delta merge: UNIQUE(intent, sector, bullet) 충돌 시 INSERT 무시 후 카운트만 UPDATE.
        """
        bullet = (bullet or "").strip()
        if not bullet or not intent:
            return
        bullet = bullet[:200]
        with self._write_lock:
            conn = self._ensure_db()
            now = time.time()
            # 신규 시도 — 충돌은 무시
            try:
                conn.execute(
                    "INSERT INTO playbook "
                    "(intent, sector, bullet, success_count, fail_count, quality, "
                    " source, created_at, last_used) VALUES (?, ?, ?, 0, 0, 0.5, ?, ?, ?)",
                    (intent, sector or "", bullet, source, now, now),
                )
            except sqlite3.IntegrityError:
                pass  # unique 충돌 — 카운트 갱신만 진행
            # 카운트/quality 갱신
            # NOTE: SQLite UPDATE의 SET expression은 OLD 값을 보므로
            # quality 식에서 +1을 명시적으로 더해야 함 (Beta posterior 근사).
            if outcome == "success":
                conn.execute(
                    "UPDATE playbook SET success_count = success_count + 1, "
                    "quality = (success_count + 2.0) / (success_count + fail_count + 3.0), "
                    "last_used = ? WHERE intent = ? AND sector = ? AND bullet = ?",
                    (now, intent, sector or "", bullet),
                )
            elif outcome == "fail":
                conn.execute(
                    "UPDATE playbook SET fail_count = fail_count + 1, "
                    "quality = (success_count + 1.0) / (success_count + fail_count + 3.0), "
                    "last_used = ? WHERE intent = ? AND sector = ? AND bullet = ?",
                    (now, intent, sector or "", bullet),
                )
            else:
                conn.execute(
                    "UPDATE playbook SET last_used = ? WHERE intent = ? AND sector = ? AND bullet = ?",
                    (now, intent, sector or "", bullet),
                )
            conn.commit()

    def get_bullets(
        self,
        intent: str,
        *,
        sector: str = "",
        limit: int = 6,
        min_quality: float = 0.4,
    ) -> list[tuple[str, float, int, int]]:
        """intent별 playbook bullet 검색 (Generator 단계 주입용).

        Args:
            intent: 정확 매칭.
            sector: 섹터 우선 매칭, 부족하면 공용("")으로 보충.
            limit: 최대 반환 수.
            min_quality: 이 값 미만은 제외 (단, neutral=0.5는 통과).

        Returns:
            ``[(bullet, quality, success, fail), ...]`` quality 내림차순.
        """
        if not intent:
            return []
        conn = self._ensure_db()
        # 섹터 우선
        rows: list[tuple[str, float, int, int]] = []
        if sector:
            rows = list(
                conn.execute(
                    "SELECT bullet, quality, success_count, fail_count FROM playbook "
                    "WHERE intent = ? AND sector = ? AND quality >= ? "
                    "ORDER BY quality DESC, last_used DESC LIMIT ?",
                    (intent, sector, min_quality, limit),
                ).fetchall()
            )
        if len(rows) < limit:
            remaining = limit - len(rows)
            seen = {r[0] for r in rows}
            extras = conn.execute(
                "SELECT bullet, quality, success_count, fail_count FROM playbook "
                "WHERE intent = ? AND sector = '' AND quality >= ? "
                "ORDER BY quality DESC, last_used DESC LIMIT ?",
                (intent, min_quality, remaining * 2),
            ).fetchall()
            for e in extras:
                if e[0] not in seen and len(rows) < limit:
                    rows.append(e)
        return rows

    def playbook_size(self, intent: str | None = None) -> int:
        """playbook 통계 — intent별 또는 전체 bullet 수."""
        conn = self._ensure_db()
        if intent:
            row = conn.execute("SELECT COUNT(*) FROM playbook WHERE intent = ?", (intent,)).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM playbook").fetchone()
        return int(row[0]) if row else 0

    # ── meta ───────────────────────────────────────────────

    def get_meta(self, key: str) -> str | None:
        conn = self._ensure_db()
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        conn = self._ensure_db()
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    # ── 마이그레이션 ───────────────────────────────────────

    def migrate_from_legacy(self) -> dict[str, int]:
        """기존 5개 분산 저장소에서 데이터를 통합 마이그레이션.

        Returns:
            각 소스별 마이그레이션된 레코드 수
        """
        current = self.get_meta("migration_version")
        if current and int(current) >= _MIGRATION_VERSION:
            return {}

        stats: dict[str, int] = {}
        conn = self._ensure_db()

        # 1. analysisMemory.db → executions
        stats["analysisMemory"] = self._migrate_analysis_memory(conn)

        # 2. skill_library.db → skills
        stats["skill_library"] = self._migrate_skill_library(conn)

        # 3. error_patterns.db → error_patterns
        stats["error_patterns"] = self._migrate_error_patterns(conn)

        # 4. audit_log.jsonl → executions
        stats["audit_log"] = self._migrate_audit_log(conn)

        # 5. auditAnalysis/*.md → insights
        stats["audit_analysis"] = self._migrate_audit_analysis(conn)

        self.set_meta("migration_version", str(_MIGRATION_VERSION))
        self.set_meta("migrated_at", str(time.time()))

        log.info("KnowledgeDB 마이그레이션 완료: %s", stats)
        return stats

    def _migrate_analysis_memory(self, conn: sqlite3.Connection) -> int:
        legacy_path = Path.home() / ".dartlab" / "analysisMemory.db"
        if not legacy_path.exists():
            return 0
        count = 0
        try:
            legacy = sqlite3.connect(str(legacy_path), timeout=5)
            # keyMetrics 컬럼 존재 여부 확인
            cols = [info[1] for info in legacy.execute("PRAGMA table_info(analysis)").fetchall()]
            has_metrics = "keyMetrics" in cols

            if has_metrics:
                rows = legacy.execute(
                    "SELECT stockCode, question, questionType, resultSummary, timestamp, grade, keyMetrics "
                    "FROM analysis ORDER BY timestamp"
                ).fetchall()
            else:
                rows = legacy.execute(
                    "SELECT stockCode, question, questionType, resultSummary, timestamp, grade "
                    "FROM analysis ORDER BY timestamp"
                ).fetchall()

            for r in rows:
                conn.execute(
                    "INSERT INTO executions "
                    "(stock_code, question, question_type, mode, result_summary, grade, key_metrics, created_at) "
                    "VALUES (?, ?, ?, 'analysis', ?, ?, ?, ?)",
                    (r[0], r[1], r[2] or "", r[3] or "", r[5] or "", r[6] if has_metrics and len(r) > 6 else "", r[4]),
                )
                count += 1
            conn.commit()
            legacy.close()
        except (sqlite3.OperationalError, OSError) as e:
            log.warning("analysisMemory 마이그레이션 실패: %s", e)
        return count

    def _migrate_skill_library(self, conn: sqlite3.Connection) -> int:
        legacy_path = Path.home() / ".dartlab" / "selfai" / "skill_library.db"
        if not legacy_path.exists():
            return 0
        count = 0
        try:
            legacy = sqlite3.connect(str(legacy_path), timeout=5)
            rows = legacy.execute(
                "SELECT question, category, tools_used, code_template, result_keys, "
                "success_count, quality_score, created_at, last_used FROM skill"
            ).fetchall()
            for r in rows:
                conn.execute(
                    "INSERT INTO skills "
                    "(question, category, tools_used, code_template, result_keys, "
                    "success_count, quality_score, mode, created_at, last_used) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 'analysis', ?, ?)",
                    r,
                )
                count += 1
            conn.commit()
            legacy.close()
        except (sqlite3.OperationalError, OSError) as e:
            log.warning("skill_library 마이그레이션 실패: %s", e)
        return count

    def _migrate_error_patterns(self, conn: sqlite3.Connection) -> int:
        legacy_path = Path.home() / ".dartlab" / "selfai" / "error_patterns.db"
        if not legacy_path.exists():
            return 0
        count = 0
        try:
            legacy = sqlite3.connect(str(legacy_path), timeout=5)
            rows = legacy.execute(
                "SELECT error_type, error_signature, wrong_code, correct_code, "
                "tool_name, frequency, last_seen FROM error_pattern"
            ).fetchall()
            for r in rows:
                conn.execute(
                    "INSERT INTO error_patterns "
                    "(error_type, error_signature, wrong_code, correct_code, "
                    "tool_name, frequency, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    r,
                )
                count += 1
            conn.commit()
            legacy.close()
        except (sqlite3.OperationalError, OSError) as e:
            log.warning("error_patterns 마이그레이션 실패: %s", e)
        return count

    def _migrate_audit_log(self, conn: sqlite3.Connection) -> int:
        audit_dir = Path(__file__).resolve().parents[4] / "data" / "dart" / "auditAi"
        log_path = audit_dir / "audit_log.jsonl"
        if not log_path.exists():
            return 0
        count = 0
        try:
            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                conn.execute(
                    "INSERT INTO executions "
                    "(stock_code, question, question_type, mode, has_error, "
                    "duration_sec, code_rounds, created_at) "
                    "VALUES (?, ?, ?, 'analysis', ?, ?, ?, ?)",
                    (
                        rec.get("stock"),
                        rec.get("question", "")[:200],
                        rec.get("id", ""),
                        int(not rec.get("passed", True)),
                        rec.get("duration"),
                        rec.get("codeRounds", 0),
                        _parse_iso_timestamp(rec.get("date", "")),
                    ),
                )
                count += 1
            conn.commit()
        except OSError as e:
            log.warning("audit_log 마이그레이션 실패: %s", e)
        return count

    def _migrate_audit_analysis(self, conn: sqlite3.Connection) -> int:
        audit_dir = Path(__file__).resolve().parents[4] / "data" / "dart" / "auditAnalysis"
        if not audit_dir.exists():
            return 0
        count = 0
        for md_path in sorted(audit_dir.glob("*.md")):
            try:
                parsed = _parse_audit_markdown(md_path)
                if parsed:
                    conn.execute(
                        "INSERT INTO insights "
                        "(stock_code, narrative, strengths, weaknesses, sector, source, "
                        "created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, 'audit', ?, ?)",
                        (
                            parsed["stock_code"],
                            parsed["narrative"],
                            json.dumps(parsed["strengths"], ensure_ascii=False),
                            json.dumps(parsed["weaknesses"], ensure_ascii=False),
                            parsed["sector"],
                            time.time(),
                            time.time() + 90 * 86400,
                        ),
                    )
                    count += 1
            except (OSError, ValueError) as e:
                log.debug("auditAnalysis 파싱 실패 %s: %s", md_path.name, e)
        conn.commit()
        return count

    # ── 통계 ───────────────────────────────────────────────

    def stats(self) -> dict[str, int]:
        conn = self._ensure_db()
        result = {}
        for table in ("executions", "skills", "error_patterns", "insights"):
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
            result[table] = row[0] if row else 0
        return result

    # ── HuggingFace 동기화 ────────────────────────────────

    def _knowledge_dir(self) -> Path:
        """공유 JSON 저장 경로: data/ai/knowledge/."""
        try:
            from dartlab import config as _cfg

            base = Path(_cfg.dataDir)
        except (ImportError, AttributeError):
            base = Path(__file__).resolve().parents[4] / "data"
        out = base / "ai" / "knowledge"
        out.mkdir(parents=True, exist_ok=True)
        return out

    def export_shared(self) -> Path:
        """공유 가능한 테이블을 data/ai/knowledge/에 JSON으로 export.

        executions(개인 질문 이력)는 프라이버시 보호를 위해 제외.

        Returns:
            export 디렉토리 경로
        """
        conn = self._ensure_db()
        out = self._knowledge_dir()

        # insights
        rows = conn.execute(
            "SELECT stock_code, narrative, strengths, weaknesses, sector, source, created_at, expires_at FROM insights"
        ).fetchall()
        insights_data = [
            {
                "stock_code": r[0],
                "narrative": r[1],
                "strengths": r[2],
                "weaknesses": r[3],
                "sector": r[4],
                "source": r[5],
                "created_at": r[6],
                "expires_at": r[7],
            }
            for r in rows
        ]
        (out / "insights.json").write_text(json.dumps(insights_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # skills
        rows = conn.execute(
            "SELECT question, category, tools_used, code_template, result_keys, "
            "success_count, quality_score, mode, created_at, last_used FROM skills"
        ).fetchall()
        skills_data = [
            {
                "question": r[0],
                "category": r[1],
                "tools_used": r[2],
                "code_template": r[3],
                "result_keys": r[4],
                "success_count": r[5],
                "quality_score": r[6],
                "mode": r[7],
                "created_at": r[8],
                "last_used": r[9],
            }
            for r in rows
        ]
        (out / "skills.json").write_text(json.dumps(skills_data, ensure_ascii=False, indent=2), encoding="utf-8")

        # error_patterns
        rows = conn.execute(
            "SELECT error_type, error_signature, wrong_code, correct_code, "
            "tool_name, frequency, last_seen FROM error_patterns"
        ).fetchall()
        errors_data = [
            {
                "error_type": r[0],
                "error_signature": r[1],
                "wrong_code": r[2],
                "correct_code": r[3],
                "tool_name": r[4],
                "frequency": r[5],
                "last_seen": r[6],
            }
            for r in rows
        ]
        (out / "error_patterns.json").write_text(
            json.dumps(errors_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # meta
        meta_data = {
            "version": _MIGRATION_VERSION,
            "exported_at": time.time(),
            "stats": {
                "insights": len(insights_data),
                "skills": len(skills_data),
                "error_patterns": len(errors_data),
            },
        }
        (out / "meta.json").write_text(json.dumps(meta_data, ensure_ascii=False, indent=2), encoding="utf-8")

        log.info(
            "export 완료 → %s (insights=%d, skills=%d, errors=%d)",
            out,
            len(insights_data),
            len(skills_data),
            len(errors_data),
        )
        return out

    def push(self, token: str | None = None) -> str:
        """data/ai/knowledge/에 export 후 HF에 업로드.

        경로: data/ai/knowledge/ → HF ai/knowledge/
        git에는 안 감 (data/ .gitignore), HF로만 동기화.

        Args:
            token: HuggingFace API 토큰 (없으면 .env에서 로드)

        Returns:
            HF URL
        """
        from huggingface_hub import HfApi

        from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

        if token is None:
            token = _load_hf_token()

        # 1. DB → data/ai/knowledge/*.json export
        out = self.export_shared()

        # 2. data/ai/knowledge/ → HF upload
        hf_dir = DATA_RELEASES["aiKnowledge"]["dir"]
        api = HfApi(token=token)

        st = self.stats()
        api.upload_folder(
            repo_id=HF_REPO,
            folder_path=str(out),
            path_in_repo=hf_dir,
            repo_type="dataset",
            commit_message=f"sync aiKnowledge: {st.get('insights', 0)} insights, {st.get('skills', 0)} skills, {st.get('error_patterns', 0)} errors",
        )

        url = f"https://huggingface.co/datasets/{HF_REPO}/tree/main/{hf_dir}"
        log.info("KnowledgeDB push 완료: %s", url)
        return url

    def pull(self, token: str | None = None, *, force: bool = False) -> dict[str, int]:
        """HF → data/ai/knowledge/ 다운로드 → 로컬 DB에 merge.

        기존 로컬 데이터를 덮어쓰지 않고 upsert한다.
        executions는 pull 대상이 아님 (프라이버시).

        Args:
            token: HuggingFace API 토큰
            force: True면 기존 데이터가 있어도 강제 다운로드

        Returns:
            테이블별 merge된 레코드 수
        """
        from huggingface_hub import hf_hub_download

        from dartlab.core.dataConfig import DATA_RELEASES, HF_REPO

        if token is None:
            token = _load_hf_token()

        hf_dir = DATA_RELEASES["aiKnowledge"]["dir"]
        out = self._knowledge_dir()
        conn = self._ensure_db()
        merge_stats: dict[str, int] = {}

        # 1. HF → data/ai/knowledge/ 다운로드
        for filename in ("insights.json", "skills.json", "error_patterns.json", "meta.json"):
            try:
                hf_hub_download(
                    repo_id=HF_REPO,
                    filename=f"{hf_dir}/{filename}",
                    repo_type="dataset",
                    local_dir=str(out.parent.parent),  # data/ 기준
                    token=token,
                    force_download=force,
                )
            except (OSError, ValueError) as e:
                log.warning("HF 다운로드 실패 (%s): %s", filename, e)

        # 2. data/ai/knowledge/*.json → DB merge
        merge_stats["insights"] = self._merge_json_to_insights(out / "insights.json", conn)
        merge_stats["skills"] = self._merge_json_to_skills(out / "skills.json", conn)
        merge_stats["error_patterns"] = self._merge_json_to_errors(out / "error_patterns.json", conn)

        log.info("KnowledgeDB pull 완료: %s", merge_stats)
        return merge_stats

    def _merge_json_to_insights(self, path: Path, conn: sqlite3.Connection) -> int:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for r in data:
            existing = conn.execute(
                "SELECT id FROM insights WHERE stock_code = ? AND source = ?",
                (r["stock_code"], r.get("source", "audit")),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO insights "
                    "(stock_code, narrative, strengths, weaknesses, sector, source, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        r["stock_code"],
                        r["narrative"],
                        r.get("strengths", "[]"),
                        r.get("weaknesses", "[]"),
                        r.get("sector", ""),
                        r.get("source", "audit"),
                        r.get("created_at", time.time()),
                        r.get("expires_at"),
                    ),
                )
                count += 1
        conn.commit()
        return count

    def _merge_json_to_skills(self, path: Path, conn: sqlite3.Connection) -> int:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for r in data:
            existing = conn.execute(
                "SELECT id FROM skills WHERE question = ? AND mode = ?",
                (r["question"], r.get("mode", "analysis")),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO skills "
                    "(question, category, tools_used, code_template, result_keys, "
                    "success_count, quality_score, mode, created_at, last_used) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        r["question"],
                        r.get("category", "general"),
                        r.get("tools_used", "[]"),
                        r["code_template"],
                        r.get("result_keys", "[]"),
                        r.get("success_count", 1),
                        r.get("quality_score", 0.8),
                        r.get("mode", "analysis"),
                        r.get("created_at", time.time()),
                        r.get("last_used", time.time()),
                    ),
                )
                count += 1
        conn.commit()
        return count

    def _merge_json_to_errors(self, path: Path, conn: sqlite3.Connection) -> int:
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for r in data:
            existing = conn.execute(
                "SELECT id, frequency FROM error_patterns WHERE error_signature = ? AND wrong_code = ?",
                (r["error_signature"], r.get("wrong_code", "")),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO error_patterns "
                    "(error_type, error_signature, wrong_code, correct_code, "
                    "tool_name, frequency, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        r["error_type"],
                        r["error_signature"],
                        r.get("wrong_code", ""),
                        r.get("correct_code", ""),
                        r.get("tool_name", ""),
                        r.get("frequency", 1),
                        r.get("last_seen", time.time()),
                    ),
                )
                count += 1
            elif existing and r.get("correct_code"):
                conn.execute(
                    "UPDATE error_patterns SET correct_code = ?, frequency = MAX(frequency, ?) WHERE id = ?",
                    (r["correct_code"], r.get("frequency", 1), existing[0]),
                )
        conn.commit()
        return count

    # ── 싱글턴 ─────────────────────────────────────────────

    def _auto_pull(self) -> None:
        """DB가 비어있으면 data/ai/knowledge/*.json에서 자동 merge.

        1순위: 로컬 data/ai/knowledge/*.json (HF 호출 없이)
        2순위: HF에서 pull (실패해도 무시)
        """
        current = self.stats()
        if current.get("insights", 0) > 0 or current.get("skills", 0) > 0:
            return  # 이미 데이터가 있으면 skip

        conn = self._ensure_db()

        # 1순위: 로컬 data/ JSON에서 merge
        local_dir = self._knowledge_dir()
        local_insights = local_dir / "insights.json"
        if local_insights.exists():
            merged = 0
            merged += self._merge_json_to_insights(local_insights, conn)
            merged += self._merge_json_to_skills(local_dir / "skills.json", conn)
            merged += self._merge_json_to_errors(local_dir / "error_patterns.json", conn)
            if merged > 0:
                log.info("auto-pull: 로컬 JSON에서 %d건 merge", merged)
                return

        # 2순위: HF pull (실패해도 무시)
        try:
            result = self.pull()
            if sum(result.values()) > 0:
                log.info("auto-pull: HF에서 %s merge", result)
        except (ImportError, OSError, ValueError) as e:
            log.debug("auto-pull HF 실패 (무시): %s", e)

    @classmethod
    def get(cls) -> KnowledgeDB:
        global _instance
        if _instance is None:
            _instance = cls()
            # 최초 접근 시 자동 마이그레이션
            try:
                _instance.migrate_from_legacy()
            except (sqlite3.OperationalError, OSError) as e:
                log.warning("KnowledgeDB 마이그레이션 실패 (무시): %s", e)
            # 마이그레이션 후 DB가 비어있으면 자동 pull
            try:
                _instance._auto_pull()
            except (sqlite3.OperationalError, OSError) as e:
                log.debug("auto-pull 실패 (무시): %s", e)
        return _instance


# ── 유틸리티 ───────────────────────────────────────────────


def _load_hf_token() -> str | None:
    """HF 토큰을 .env 또는 환경변수에서 로드."""
    import os

    token = os.environ.get("HF_TOKEN")
    if token:
        return token
    try:
        from dotenv import load_dotenv

        load_dotenv()
        return os.environ.get("HF_TOKEN")
    except ImportError:
        return None


def _parse_iso_timestamp(iso_str: str) -> float:
    """ISO 타임스탬프를 Unix timestamp로 변환."""
    if not iso_str:
        return time.time()
    try:
        import datetime

        dt = datetime.datetime.fromisoformat(iso_str)
        return dt.timestamp()
    except (ValueError, TypeError):
        return time.time()


def _parse_audit_markdown(path: Path) -> dict | None:
    """auditAnalysis 마크다운 파일에서 인사이트를 추출.

    구조:
    - [+] 강점
    - [-] 약점
    - > **재무 순환 서사** ... (narrative)
    - 섹터: ...
    """
    stock_code = path.stem
    if not re.match(r"\d{6}", stock_code):
        return None

    text = path.read_text(encoding="utf-8")
    if len(text) < 100:
        return None

    # 강점/약점 추출
    strengths = re.findall(r"\[\+\]\s*(.+)", text)
    weaknesses = re.findall(r"\[-\]\s*(.+)", text)

    # 서사 추출 (재무 순환 서사 블록)
    narrative = ""
    narrative_match = re.search(
        r">\s*\*\*재무 순환 서사\*\*\s*\n((?:>\s*.+\n?)+)",
        text,
    )
    if narrative_match:
        raw = narrative_match.group(1)
        narrative = re.sub(r"^>\s*", "", raw, flags=re.MULTILINE).strip()

    if not narrative:
        # fallback: 첫 번째 [+] 라인을 서사로
        if strengths:
            narrative = strengths[0]
        else:
            return None

    # 섹터 추출
    sector = ""
    sector_match = re.search(r"섹터:\s*(.+?)(?:\s*\||$)", text)
    if sector_match:
        sector = sector_match.group(1).strip()

    return {
        "stock_code": stock_code,
        "narrative": narrative[:_MAX_INSIGHT_NARRATIVE],
        "strengths": strengths[:10],
        "weaknesses": weaknesses[:10],
        "sector": sector,
    }
