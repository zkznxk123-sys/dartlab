"""Intent 분류 — 질문 → 6막 + compare + concept.

LLM 호출 없이 키워드 매칭 + Company 상태 + 패턴으로 결정론적 분류.
selfai 폐기 학습 적용: ML 없음, 모든 규칙은 명시적 코드.

8개 Intent:
    act1_business    — 사업이해 (수익구조, 성장성)
    act2_profit      — 수익성 (마진, 비용구조)
    act3_cash        — 현금흐름 (CF, 이익품질)
    act4_stability   — 안정성 (부채, 신용)
    act5_capital     — 자본배분 (배당, ROIC)
    act6_outlook     — 전망 (가치평가, 매크로)
    compare          — 시장 비교 (scan)
    concept          — 개념질문 (capabilities, docs)

오분류 fallback: act_all (전체 14축 요약 주입)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    ACT1_BUSINESS = "act1_business"
    ACT2_PROFIT = "act2_profit"
    ACT3_CASH = "act3_cash"
    ACT4_STABILITY = "act4_stability"
    ACT5_CAPITAL = "act5_capital"
    ACT6_OUTLOOK = "act6_outlook"
    COMPARE = "compare"
    CONCEPT = "concept"
    ACT_ALL = "act_all"  # fallback — 의도가 명확하지 않거나 종합 질문


# ── 키워드 사전 ────────────────────────────────────────────
# 각 막에 배타적으로 강한 신호만 등록. 약한 키워드는 act_all로 떨어져도 OK.

_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.ACT1_BUSINESS: (
        "사업", "비즈니스", "매출구성", "사업부", "세그먼트", "segment",
        "제품", "서비스", "고객", "시장점유", "시장 점유", "성장",
        "뭐하는", "뭘 하는", "어떤 회사", "뭐 해서", "뭐해서",
        "돈 벌", "돈벌", "수익원",
    ),
    Intent.ACT2_PROFIT: (
        "수익성", "마진", "영업이익률", "순이익률", "ROIC", "ROE", "ROA",
        "비용구조", "원가", "판관비", "이익률", "수익", "벌고",
    ),
    Intent.ACT3_CASH: (
        "현금", "현금흐름", "OCF", "FCF", "이익품질", "운전자본",
        "감가상각", "발생액", "현금전환",
    ),
    Intent.ACT4_STABILITY: (
        "부채", "안정성", "재무건전", "이자보상", "유동", "차입",
        "신용", "부실", "Z-Score", "ICR", "디폴트", "default",
    ),
    Intent.ACT5_CAPITAL: (
        "배당", "자사주", "자본배분", "주주환원", "유보", "재투자",
        "CAPEX", "WACC",
    ),
    Intent.ACT6_OUTLOOK: (
        "전망", "예측", "추정", "valuation", "DCF", "PER", "PBR",
        "목표가", "적정가", "고평가", "저평가", "안전마진",
        "매크로", "환율", "금리", "유가",
    ),
    Intent.COMPARE: (
        "비교", "랭킹", "순위", "상위", "하위", "대비", "vs", "VS",
        "동종", "동종업계", "peer", "scan", "스캔", "전종목",
        "업종 평균", "업종평균",
        # NOTE: "보다 큰/작은/높/낮" 은 두 지표 간 비교에도 자주 쓰여 제외.
        # COMPARE 는 회사 간 비교일 때만 매칭되도록 명시적 키워드만 둔다.
    ),
    Intent.CONCEPT: (
        "사용법", "어떻게 쓰", "어떻게 사용", "어떻게 호출",
        "방법 알려", "예시", "예제", "튜토리얼",
        "dartlab", "ask(", "show(", "select(", "analysis(", "review(",
        "공시 어디", "어디서 찾",
    ),
}


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    confidence: float  # 0.0~1.0 — 매칭된 키워드 / 후보 키워드 비율
    matchedKeywords: tuple[str, ...]


def _scoreIntent(question: str, intent: Intent) -> tuple[float, tuple[str, ...]]:
    """단일 intent 점수 + 매칭된 키워드 반환."""
    q = question.lower()
    keywords = _KEYWORDS[intent]
    matched = tuple(kw for kw in keywords if kw.lower() in q)
    if not matched:
        return 0.0, ()
    # 매칭 키워드 수 / 후보 수 — 정규화. 단순 카운트 우선.
    score = len(matched) / max(len(keywords), 1)
    # 매칭 1개라도 있으면 최소 0.2 보장 (희소 키워드 보호)
    return max(score, 0.2), matched


def classifyIntent(
    question: str,
    *,
    hasCompany: bool = False,
) -> IntentResult:
    """질문 → IntentResult.

    Args:
        question: 사용자 질문
        hasCompany: Company 객체 존재 여부 (없으면 CONCEPT/COMPARE 가중치)

    Returns:
        IntentResult — 가장 높은 점수의 intent. 동점은 정의 순서.
    """
    if not question or not question.strip():
        return IntentResult(Intent.ACT_ALL, 0.0, ())

    scores: list[tuple[Intent, float, tuple[str, ...]]] = []
    for intent in (
        Intent.COMPARE,  # compare 먼저 — "비교" 키워드가 다른 막과 섞일 때 우선
        Intent.CONCEPT,
        Intent.ACT2_PROFIT,
        Intent.ACT3_CASH,
        Intent.ACT4_STABILITY,
        Intent.ACT5_CAPITAL,
        Intent.ACT6_OUTLOOK,
        Intent.ACT1_BUSINESS,
    ):
        score, matched = _scoreIntent(question, intent)
        if score > 0:
            scores.append((intent, score, matched))

    if not scores:
        return IntentResult(Intent.ACT_ALL, 0.0, ())

    # Company 없으면 막 관련 intent는 의미 없음 → CONCEPT/COMPARE 우대
    if not hasCompany:
        prioritized = [s for s in scores if s[0] in (Intent.CONCEPT, Intent.COMPARE)]
        if prioritized:
            scores = prioritized

    # 최고 점수 선택 (동점은 위 순서 유지)
    scores.sort(key=lambda s: s[1], reverse=True)
    best = scores[0]
    return IntentResult(best[0], best[1], best[2])
