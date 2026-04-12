"""ExperienceIndex — KnowledgeDB.executions 위의 과거 성공 사례 검색.

핵심 사상: AI가 절차적 학습을 못 해도, 과거 성공한 호출을
in-context few-shot으로 재주입하면 "경험 기반 학습" 효과.
(뇌과학: 해마 consolidation 등가, 정보과학: I(example;θ) 극대화)

하부 엔진이 바뀌어도 새 성공 사례가 축적되며 자동 적응.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExperienceHit:
    """과거 성공 사례."""

    question: str
    code: str
    result_summary: str
    grade: str
    age_days: float
    score: float

    def toPromptText(self) -> str:
        """프롬프트 주입용 형식. 질문 + 성공 코드."""
        code_preview = self.code[:800]
        return (
            f"### 유사 질문: {self.question[:120]}\n"
            f"성공한 코드:\n```python\n{code_preview}\n```\n"
        )


class ExperienceIndex:
    """KnowledgeDB.executions 위의 과거 성공 사례 인덱스.

    임베딩 없이 키워드 기반 매칭. 등급 P(Pass) + 최신성 우선.
    """

    def __init__(self) -> None:
        pass

    def search(
        self,
        query: str,
        *,
        stockCode: str | None = None,
        k: int = 3,
        minGrade: str = "P",
        maxAgeDays: int = 180,
    ) -> list[ExperienceHit]:
        """성공한 유사 사례 검색.

        Args:
            query: 현재 질문
            stockCode: 같은 종목 우선 (있으면 가점)
            k: 반환 개수
            minGrade: 최소 등급 (P=Pass 이상만)
            maxAgeDays: 이 일수 이내만

        Returns:
            score 내림차순 상위 k개. 빈 리스트면 fresh start.
        """
        try:
            from dartlab.ai.persistence.knowledge_db import KnowledgeDB
        except ImportError:
            return []

        try:
            db = KnowledgeDB.get()
            conn = db._ensure_db()
        except (ImportError, OSError) as e:
            log.debug("ExperienceIndex: DB 접근 실패 %s", e)
            return []

        now = time.time()
        cutoff = now - (maxAgeDays * 86400)

        try:
            rows = conn.execute(
                """
                SELECT stock_code, question, result_summary, grade, created_at, key_metrics
                FROM executions
                WHERE created_at >= ? AND has_error = 0
                ORDER BY created_at DESC
                LIMIT 500
                """,
                (cutoff,),
            ).fetchall()
        except Exception as e:
            log.debug("ExperienceIndex: 쿼리 실패 %s", e)
            return []

        if not rows:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        hits: list[ExperienceHit] = []
        allowed_grades = self._gradeFilter(minGrade)

        for row in rows:
            row_stock = row[0] or ""
            row_question = row[1]
            row_summary = row[2] or ""
            row_grade = row[3] or ""
            row_created = row[4]

            # 등급 필터
            if allowed_grades and row_grade and row_grade not in allowed_grades:
                continue

            # 스코어 계산
            q_tokens = self._tokenize(row_question)
            if not q_tokens:
                continue

            # Jaccard 유사도 + 종목 일치 가점 + 최신성 가점
            overlap = len(set(query_tokens) & set(q_tokens))
            if overlap == 0:
                continue
            jaccard = overlap / len(set(query_tokens) | set(q_tokens))

            score = jaccard * 10.0
            if stockCode and row_stock == stockCode:
                score += 3.0

            age_days = (now - row_created) / 86400
            score *= max(0.3, 1.0 - age_days / maxAgeDays)

            # code는 executions 테이블에 직접 저장되지 않음.
            # key_metrics 나 result_summary 에서 코드 추출 시도.
            code = self._extractCode(row_summary) or row[5] or ""

            hits.append(
                ExperienceHit(
                    question=row_question,
                    code=code,
                    result_summary=row_summary[:500],
                    grade=row_grade,
                    age_days=age_days,
                    score=score,
                )
            )

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def accumulate(
        self,
        question: str,
        code: str,
        result_summary: str,
        grade: str = "P",
        *,
        stockCode: str | None = None,
        question_type: str = "",
    ) -> None:
        """새 성공 사례 저장.

        analyze() 완료 시 자동 호출. grade는 실행 성공/에러 없음/결과 출력 기준 자동 판정.
        code는 result_summary에 섞어서 저장 (executions 스키마 확장 피함).
        """
        try:
            from dartlab.ai.persistence.knowledge_db import KnowledgeDB
        except ImportError:
            return

        try:
            db = KnowledgeDB.get()
            # result_summary 앞에 실행 코드 저장 (나중에 추출 가능)
            summary_with_code = f"__CODE_START__\n{code[:3000]}\n__CODE_END__\n{result_summary[:2000]}"
            db.save_execution(
                stock_code=stockCode or "",
                question=question,
                question_type=question_type,
                result_summary=summary_with_code,
                grade=grade,
            )
        except (ImportError, OSError) as e:
            log.debug("ExperienceIndex accumulate 실패 %s", e)

    def formatForPrompt(self, hits: list[ExperienceHit]) -> str:
        """검색 결과를 프롬프트 주입용 마크다운으로 포맷."""
        if not hits:
            return ""
        lines = ["## 과거 성공 분석 사례 (참고용 — 패턴만 흉내내라)"]
        for hit in hits:
            lines.append("")
            lines.append(hit.toPromptText())
        return "\n".join(lines)

    # ── 내부 유틸 ──

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[가-힣]+|[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        return [t for t in tokens if len(t) >= 2]

    def _gradeFilter(self, minGrade: str) -> set[str]:
        """등급 필터. P 이상 = {P, G} (Pass, Good)."""
        order = {"V": 0, "C": 1, "T": 2, "P": 3, "G": 4}
        min_level = order.get(minGrade, 3)
        return {g for g, lv in order.items() if lv >= min_level}

    def _extractCode(self, summary: str) -> str | None:
        """result_summary에 저장된 코드 추출."""
        if not summary:
            return None
        m = re.search(r"__CODE_START__\n(.*?)\n__CODE_END__", summary, re.DOTALL)
        return m.group(1) if m else None


# 싱글턴
_instance: ExperienceIndex | None = None


def getExperienceIndex() -> ExperienceIndex:
    """싱글턴 ExperienceIndex 인스턴스."""
    global _instance
    if _instance is None:
        _instance = ExperienceIndex()
    return _instance
