"""ACE playbook 단위 테스트.

scope:
- KnowledgeDB.upsert_bullet/get_bullets — delta merge + 카운트 갱신
- playbook.extractBullets — 헤더/리스트 추출
- playbook.gradeToOutcome — G/T/C/V/P 매핑
- playbook.curate — end-to-end Curator 동작
- selectPlaybookBullets — ContextPart 변환
- ContextBuilder 통합 — playbook bullets가 bundle에 들어옴
"""

from __future__ import annotations

import pytest

from dartlab.ai.context.playbook import (
    curate,
    extractBullets,
    gradeToOutcome,
    retrieveBullets,
)
from dartlab.ai.context.selectors.playbook import selectPlaybookBullets
from dartlab.ai.persistence.knowledge_db import KnowledgeDB

pytestmark = pytest.mark.unit


@pytest.fixture
def db(tmp_path, monkeypatch):
    """격리된 임시 DB — 다른 테스트와 충돌 없음."""
    db_path = tmp_path / "test_playbook.db"
    inst = KnowledgeDB(db_path=db_path)
    # 싱글톤 우회: 직접 인스턴스 사용 + curate가 부르는 KnowledgeDB.get() 도 이걸로
    monkeypatch.setattr(KnowledgeDB, "get", classmethod(lambda cls: inst))
    yield inst
    inst.close()


# ── extractBullets ────────────────────────────────────────


class TestExtractBullets:
    def test_empty(self):
        assert extractBullets("") == []

    def test_header_pattern(self):
        text = "분석 결과...\n결론: 마진은 사이클 정점에서 압박받는다.\n"
        bullets = extractBullets(text)
        assert any("사이클 정점" in b for b in bullets)

    def test_markdown_list(self):
        text = "주요 관찰:\n- ROIC 12% 유지\n- 부채비율 하락 추세\n"
        bullets = extractBullets(text)
        assert len(bullets) >= 2
        assert any("ROIC" in b for b in bullets)

    def test_skip_short_noise(self):
        text = "- 있다\n- 분석\n- 정상적인 의미 있는 한 줄 코멘트입니다"
        bullets = extractBullets(text)
        # 노이즈는 제외
        assert "있다" not in bullets
        assert any("정상적인" in b for b in bullets)

    def test_skip_table_lines(self):
        text = "- | a | b | c | d |\n- 진짜 인사이트가 여기 있다는 사실"
        bullets = extractBullets(text)
        assert all("|" not in b or b.count("|") < 3 for b in bullets)

    def test_dedupe(self):
        text = "결론: 같은 문장입니다 반복\n- 같은 문장입니다 반복"
        bullets = extractBullets(text)
        seen_count = sum(1 for b in bullets if "같은 문장입니다 반복" in b)
        assert seen_count == 1


# ── gradeToOutcome ────────────────────────────────────────


class TestGradeToOutcome:
    def test_good(self):
        assert gradeToOutcome("G") == "success"

    def test_partial(self):
        assert gradeToOutcome("P") == "success"

    def test_crash(self):
        assert gradeToOutcome("C") == "fail"

    def test_vague(self):
        assert gradeToOutcome("V") == "fail"

    def test_trivial_neutral(self):
        assert gradeToOutcome("T") == "neutral"

    def test_empty(self):
        assert gradeToOutcome("") == "neutral"
        assert gradeToOutcome(None) == "neutral"


# ── KnowledgeDB delta merge ───────────────────────────────


class TestPlaybookCRUD:
    def test_upsert_new(self, db):
        db.upsert_bullet("act2_profit", "마진은 사이클 정점에서 압박", outcome="success")
        rows = db.get_bullets("act2_profit", min_quality=0.0)
        assert len(rows) == 1
        bullet, quality, success, fail = rows[0]
        assert "사이클 정점" in bullet
        assert success == 1
        assert fail == 0

    def test_delta_merge_increments(self, db):
        # 같은 bullet 3회 success → success_count = 3
        for _ in range(3):
            db.upsert_bullet("act2_profit", "동일한 한 줄 인사이트입니다", outcome="success")
        rows = db.get_bullets("act2_profit", min_quality=0.0)
        assert len(rows) == 1  # delta merge — 1행
        _, quality, success, fail = rows[0]
        assert success == 3
        assert quality > 0.5

    def test_fail_decreases_quality(self, db):
        db.upsert_bullet("act2_profit", "잘못된 한 줄 가설입니다", outcome="success")
        for _ in range(5):
            db.upsert_bullet("act2_profit", "잘못된 한 줄 가설입니다", outcome="fail")
        rows = db.get_bullets("act2_profit", min_quality=0.0)
        assert len(rows) == 1
        _, quality, success, fail = rows[0]
        assert fail == 5
        assert quality < 0.5

    def test_get_bullets_quality_filter(self, db):
        db.upsert_bullet("act2_profit", "고품질 인사이트입니다 매우 좋음", outcome="success")
        db.upsert_bullet("act2_profit", "고품질 인사이트입니다 매우 좋음", outcome="success")
        # 낮은 품질
        db.upsert_bullet("act2_profit", "낮은 품질 인사이트입니다 별로", outcome="fail")
        db.upsert_bullet("act2_profit", "낮은 품질 인사이트입니다 별로", outcome="fail")
        db.upsert_bullet("act2_profit", "낮은 품질 인사이트입니다 별로", outcome="fail")

        # min_quality 0.5 → 고품질만
        rows = db.get_bullets("act2_profit", min_quality=0.5)
        bullets = [r[0] for r in rows]
        assert any("고품질" in b for b in bullets)
        assert not any("낮은 품질" in b for b in bullets)

    def test_sector_priority(self, db):
        # 섹터 전용 + 공용 둘 다 있을 때 섹터 우선
        db.upsert_bullet("act2_profit", "공용 인사이트 한 줄입니다", sector="", outcome="success")
        db.upsert_bullet("act2_profit", "반도체 전용 한 줄 인사이트입니다", sector="반도체", outcome="success")

        rows = db.get_bullets("act2_profit", sector="반도체", min_quality=0.0, limit=2)
        bullets = [r[0] for r in rows]
        # 섹터 전용이 먼저, 그 다음 공용 보충
        assert any("반도체 전용" in b for b in bullets)

    def test_playbook_size(self, db):
        assert db.playbook_size("act2_profit") == 0
        db.upsert_bullet("act2_profit", "첫 번째 한 줄 bullet", outcome="success")
        db.upsert_bullet("act3_cash", "두 번째 한 줄 bullet", outcome="success")
        assert db.playbook_size("act2_profit") == 1
        assert db.playbook_size() == 2


# ── curate end-to-end ─────────────────────────────────────


class TestCurate:
    def test_curate_extracts_and_stores(self, db):
        response = (
            "분석 결과...\n"
            "결론: 영업이익률이 사이클 정점을 통과했다 — 마진 압박 시작.\n"
            "- ROIC 15% 유지로 자본효율은 우수\n"
            "- 재고 회전이 느려지는 추세 주의\n"
        )
        result = curate(
            intent="act2_profit",
            response_text=response,
            grade="G",
            sector="반도체",
        )
        assert result.inserted >= 2
        # retrieval로 확인
        bullets = retrieveBullets("act2_profit", sector="반도체", min_quality=0.0)
        assert len(bullets) >= 2

    def test_curate_empty_response(self, db):
        result = curate(intent="act2_profit", response_text="", grade="G")
        assert result.inserted == 0

    def test_curate_no_intent(self, db):
        result = curate(intent="", response_text="결론: 뭔가 있다", grade="G")
        assert result.inserted == 0

    def test_curate_fail_outcome(self, db):
        response = "결론: 분명히 가설이 잘못되었다 명시적으로"
        curate(intent="act4_stability", response_text=response, grade="C")
        # fail 카운트 1, quality < 0.5
        rows = retrieveBullets("act4_stability", min_quality=0.0)
        assert len(rows) == 1


# ── selector ──────────────────────────────────────────────


class _FakeCompany:
    stockCode = "005930"
    corpName = "삼성전자"
    sector = "반도체"


class TestSelectPlaybookBullets:
    def test_empty_intent_returns_nothing(self, db):
        parts = selectPlaybookBullets("", _FakeCompany())
        assert parts == []

    def test_act_all_returns_nothing(self, db):
        parts = selectPlaybookBullets("act_all", _FakeCompany())
        assert parts == []

    def test_no_bullets_returns_nothing(self, db):
        parts = selectPlaybookBullets("act2_profit", _FakeCompany())
        assert parts == []

    def test_with_bullets_returns_part(self, db):
        # 미리 bullet 등록
        db.upsert_bullet("act2_profit", "사이클 정점 마진 압박 주의", sector="반도체", outcome="success")
        db.upsert_bullet("act2_profit", "사이클 정점 마진 압박 주의", sector="반도체", outcome="success")

        parts = selectPlaybookBullets("act2_profit", _FakeCompany())
        assert len(parts) == 1
        part = parts[0]
        assert part.key == "ace.playbook"
        assert "사이클 정점" in part.text
        assert "playbook" in part.text


# ── ContextBuilder 통합 ───────────────────────────────────


class TestContextBuilderWithPlaybook:
    def test_builder_includes_playbook_when_available(self, db):
        from dartlab.ai.context import ContextBuilder

        # bullet 미리 등록
        db.upsert_bullet("act2_profit", "마진 압박 사이클 정점 통과", outcome="success")
        db.upsert_bullet("act2_profit", "마진 압박 사이클 정점 통과", outcome="success")

        c = _FakeCompany()
        bundle = ContextBuilder(
            question="영업이익률 추세는?",
            company=c,
            provider="gemini",
        ).build()

        assert bundle.intent == "act2_profit"
        assert "ace.playbook" in bundle.keys()
