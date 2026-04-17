"""ACE Curator/Reflector — dartlab 결정론 구현.

역할 (Phase 16 C3): **WRITE 전용** — 신규 bullet 저장/learning (delta merge).
조회/READ 경로는 `ai/insights.py` (pastInsight/sectorInsights).

논문: arxiv.org/abs/2510.04618 (ICLR 2026, Stanford+UCB+SambaNova)

ACE 3 컴포넌트 매핑:
    Generator  = ai/runtime/core.py::_streamWithCodeExecution (이미 있음)
    Reflector  = extractBullets() — 응답 텍스트에서 bullet 추출 (결정론)
    Curator    = curate() — KnowledgeDB.upsert_bullet 위임 (delta merge)

핵심 규칙 (논문):
    1. delta merge — 기존 bullet 절대 삭제 X. context collapse 방지.
    2. bullet은 한 줄 (200자 cap), 중첩 금지.
    3. success/fail 카운트 → quality (Beta posterior 근사).
    4. retrieval은 quality desc, 섹터 우선 매칭.

selfai 폐기 학습 적용:
    - LLM Reflector 안 씀 (페이퍼는 LLM Reflector 사용).
    - dartlab은 결정론 regex/패턴 추출만 — 디버깅 가능, 토큰 비용 0.
    - 효과 검증 후 LLM Reflector 단계 도입 검토.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Reflector: 응답 → bullet 결정론 추출 ───────────────────

# 의미 있는 한 줄 패턴 (한국어 분석 응답 기준)
_BULLET_HEADERS = (
    "결론",
    "핵심",
    "요약",
    "판단",
    "주의",
    "리스크",
    "강점",
    "약점",
    "관전",
    "관찰",
)

_BULLET_LINE_RE = re.compile(
    r"^\s*[-*•]\s*(.+?)$",
    re.MULTILINE,
)

_HEADER_LINE_RE = re.compile(
    rf"(?:{'|'.join(_BULLET_HEADERS)})[:：]\s*([^\n]{{8,180}})",
)

# 너무 짧거나 무의미한 패턴 차단
_NOISE_RE = re.compile(r"^(있다|없다|확인|분석|참고|참조)\.?$")


def _cleanBullet(text: str) -> str | None:
    """bullet 정제 — 길이/노이즈 필터."""
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("-*•·#> .").strip()
    if not text:
        return None
    if len(text) < 8 or len(text) > 200:
        return None
    if _NOISE_RE.match(text):
        return None
    # 코드/표 라인 제외
    if "|" in text and text.count("|") >= 3:
        return None
    if text.startswith("```"):
        return None
    return text


def extractBullets(response_text: str, *, max_bullets: int = 8) -> list[str]:
    """응답 텍스트 → 핵심 bullet 리스트.

    추출 우선순위:
    1. "결론:", "핵심:", "주의:" 등 헤더 매칭 (가장 신뢰)
    2. 마크다운 리스트 항목 (- / * / •)
    3. 위 둘 다 없으면 빈 리스트 (조용히 실패)
    """
    if not response_text:
        return []
    bullets: list[str] = []
    seen: set[str] = set()

    # 1. 헤더 매칭
    for m in _HEADER_LINE_RE.finditer(response_text):
        cleaned = _cleanBullet(m.group(1))
        if cleaned and cleaned not in seen:
            bullets.append(cleaned)
            seen.add(cleaned)
            if len(bullets) >= max_bullets:
                return bullets

    # 2. 마크다운 리스트
    for m in _BULLET_LINE_RE.finditer(response_text):
        cleaned = _cleanBullet(m.group(1))
        if cleaned and cleaned not in seen:
            bullets.append(cleaned)
            seen.add(cleaned)
            if len(bullets) >= max_bullets:
                return bullets

    return bullets


# ── grade → outcome 매핑 ──────────────────────────────────


def gradeToOutcome(grade: str | None) -> str:
    """KnowledgeDB executions.grade → upsert_bullet outcome.

    dartlab grade 체계:
        G — Good (성공)
        T — Trivial (보통, neutral)
        C — Crash (실패)
        V — Vague (실패 — 모호한 답변)
        P — Partial (성공 — 부분적이지만 가치 있음)
    """
    g = (grade or "").upper().strip()
    if g in ("G", "P"):
        return "success"
    if g in ("C", "V"):
        return "fail"
    return "neutral"


# ── Curator: bullet 묶음을 KnowledgeDB로 영속 ────────────


@dataclass
class CurateResult:
    intent: str
    sector: str
    inserted: int
    skipped: int


def curate(
    *,
    intent: str,
    response_text: str,
    grade: str | None,
    sector: str = "",
    source: str = "reflection",
) -> CurateResult:
    """Reflector + Curator 한 번에 호출.

    1. extractBullets — 결정론 추출
    2. gradeToOutcome — success/fail/neutral 결정
    3. KnowledgeDB.upsert_bullet — delta merge

    실패 (DB 없음/import 실패) 시 빈 결과 반환, 예외 전파 X.
    """
    if not intent or not response_text:
        return CurateResult(intent or "", sector, 0, 0)

    bullets = extractBullets(response_text)
    if not bullets:
        return CurateResult(intent, sector, 0, 0)

    outcome = gradeToOutcome(grade)
    inserted = 0
    skipped = 0
    from dartlab.ai.persistence import _get_db

    db = _get_db()
    if db is None:
        return CurateResult(intent, sector, 0, len(bullets))

    for b in bullets:
        try:
            db.upsert_bullet(
                intent=intent,
                bullet=b,
                sector=sector,
                outcome=outcome,
                source=source,
            )
            inserted += 1
        except (OSError, RuntimeError):
            skipped += 1

    return CurateResult(intent, sector, inserted, skipped)


# ── Generator 측: bullet retrieval ─────────────────────────


def retrieveBullets(
    intent: str,
    *,
    sector: str = "",
    limit: int = 6,
    min_quality: float = 0.4,
) -> list[str]:
    """intent별 playbook bullet retrieval.

    ContextBuilder 의 selector 가 호출. KnowledgeDB 없거나 비어있으면 빈 리스트.
    """
    if not intent:
        return []
    from dartlab.ai.persistence import _get_db

    db = _get_db()
    if db is None:
        return []
    try:
        rows = db.get_bullets(
            intent=intent,
            sector=sector,
            limit=limit,
            min_quality=min_quality,
        )
    except (OSError, RuntimeError):
        return []
    return [r[0] for r in rows]


# ── 자기성장 인사이트 갱신 (core.py 에서 이동) ─────────────────
#
# 사상: AI 응답에서 강점/약점/서사를 regex 로 추출 → KnowledgeDB.insights
# 갱신. LLM 호출 없이 결정론적. curate() (bullet) 와 같은 post-response 훅.

import re as _re

_STRENGTH_RE = _re.compile(
    r"(?:강점|장점|긍정|양호|우수|탄탄|회복|개선|성장|확대|증가|상승|반등)[:\s은는이가\.]+([^\n]{5,120})",
)
_WEAKNESS_RE = _re.compile(
    r"(?:약점|리스크|위험|부정|주의|훼손|악화|하락|감소|취약|부진|침체|압박|우려)[:\s은는이가\.]+([^\n]{5,120})",
)
_NARRATIVE_RE = _re.compile(r"(?:결론|종합|요약|핵심|핵심 판단)[:\s]*(.+?)(?:\n\n|\Z)", _re.DOTALL)


def saveInsightFromResponse(
    stock_code: str,
    response_text: str,
    company: Any | None = None,
) -> None:
    """AI 응답에서 인사이트 추출 → KnowledgeDB 저장. curate 와 병렬 훅."""
    from dartlab.ai.persistence import _get_db

    strengths = _STRENGTH_RE.findall(response_text)
    weaknesses = _WEAKNESS_RE.findall(response_text)

    narrative = ""
    match = _NARRATIVE_RE.search(response_text)
    if match:
        narrative = match.group(1).strip()[:500]
    if not narrative:
        clean = _re.sub(r"```[\s\S]*?```", "", response_text)
        clean = _re.sub(r"\|.*\|", "", clean).strip()
        if clean:
            narrative = clean[:200]
    if not narrative:
        return

    sector = ""
    if company is not None:
        sector = getattr(company, "sector", None) or getattr(company, "sectorName", None) or ""

    db = _get_db()
    if db is None:
        return
    try:
        db.save_insight(
            stock_code=stock_code,
            narrative=narrative,
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
            sector=str(sector),
            source="live",
        )
    except (OSError, RuntimeError):
        pass
