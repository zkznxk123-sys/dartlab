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

오분류 fallback: act_all (핵심 축 요약 주입)
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


class Category(str, Enum):
    """질문 상위 범주 — dartlab 경유 강제력 결정.

    META: dartlab 자체 안내 (tool 불필요, 프롬프트+CAPABILITIES 로 답)
    FINANCE: 금융 분석 (tool 최소 1회 강제, tool_choice=any 첫 라운드)
    OUT_OF_SCOPE: 비금융 (짧게 답 + "범위 밖" 명시, tool 금지)
    """

    META = "meta"
    FINANCE = "finance"
    OUT_OF_SCOPE = "out_of_scope"


# ── 키워드 사전 ────────────────────────────────────────────
# 각 막에 배타적으로 강한 신호만 등록. 약한 키워드는 act_all로 떨어져도 OK.

_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.ACT1_BUSINESS: (
        "사업",
        "비즈니스",
        "매출구성",
        "사업부",
        "세그먼트",
        "segment",
        "제품",
        "서비스",
        "고객",
        "시장점유",
        "시장 점유",
        "성장",
        "뭐하는",
        "뭘 하는",
        "어떤 회사",
        "뭐 해서",
        "뭐해서",
        "돈 벌",
        "돈벌",
        "수익원",
    ),
    Intent.ACT2_PROFIT: (
        "수익성",
        "마진",
        "영업이익률",
        "순이익률",
        "ROIC",
        "ROE",
        "ROA",
        "비용구조",
        "원가",
        "판관비",
        "이익률",
        "수익",
        "벌고",
    ),
    Intent.ACT3_CASH: (
        "현금",
        "현금흐름",
        "OCF",
        "FCF",
        "이익품질",
        "운전자본",
        "감가상각",
        "발생액",
        "현금전환",
    ),
    Intent.ACT4_STABILITY: (
        "부채",
        "안정성",
        "재무건전",
        "이자보상",
        "유동",
        "차입",
        "신용",
        "부실",
        "Z-Score",
        "ICR",
        "디폴트",
        "default",
    ),
    Intent.ACT5_CAPITAL: (
        "배당",
        "자사주",
        "자본배분",
        "주주환원",
        "유보",
        "재투자",
        "CAPEX",
        "WACC",
    ),
    Intent.ACT6_OUTLOOK: (
        "전망",
        "예측",
        "추정",
        "valuation",
        "DCF",
        "PER",
        "PBR",
        "목표가",
        "적정가",
        "고평가",
        "저평가",
        "안전마진",
        "매크로",
        "환율",
        "금리",
        "유가",
        "경기",
        "사이클",
        "cycle",
        "불황",
        "호황",
        "침체",
        "확장",
    ),
    Intent.COMPARE: (
        "비교",
        "랭킹",
        "순위",
        "상위",
        "하위",
        "대비",
        "vs",
        "VS",
        "동종",
        "동종업계",
        "peer",
        "scan",
        "스캔",
        "전종목",
        "업종 평균",
        "업종평균",
        "증가한 회사",
        "감소한 회사",
        "좋은 회사",
        "나쁜 회사",
        "추천",
        "업종",
        "회사 찾",
        "어떤 회사가",
        "어디가 좋",
    ),
    Intent.CONCEPT: (
        "사용법",
        "어떻게 쓰",
        "어떻게 사용",
        "어떻게 호출",
        "방법 알려",
        "예시",
        "예제",
        "튜토리얼",
        "dartlab",
        "ask(",
        "show(",
        "select(",
        "analysis(",
        "review(",
        "공시 어디",
        "어디서 찾",
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


# ── 3분류 범주 분류기 ──────────────────────────────────────────
#
# META: dartlab 자체 (capabilities/사용법) → tool 불필요
# FINANCE: 기업/시장/매크로/공시/가치/신용 → tool 강제
# OUT_OF_SCOPE: 날씨/일상/일반 코딩 → 거절 + 범위 밖 명시
#
# 사상: 모호하면 FINANCE (기본값) — 오탐 금지. OUT_OF_SCOPE 는 명백한 비금융만.

_META_KEYWORDS: tuple[str, ...] = (
    "dartlab",
    "DartLab",
    "뭐 할 수 있",
    "뭐할 수 있",
    "뭐 할수 있",
    "어떤 기능",
    "어떤 도구",
    "capabilities",
    "capability",
    "사용법",
    "어떻게 쓰",
    "어떻게 사용",
    "어떻게 호출",
    "어떻게 설치",
    "설치 방법",
    "튜토리얼",
    "예시 보여",
    "예제",
    "명령어",
    "도움말",
    "help",
)

# OUT_OF_SCOPE 판정: 금융 키워드 0개 + 아래 일반 주제 키워드 중 하나 이상
_GENERAL_TOPIC_KEYWORDS: tuple[str, ...] = (
    # 날씨/일상
    "날씨",
    "온도",
    "비와",
    "눈와",
    "기온",
    "미세먼지",
    # 일반 코딩 (dartlab 이 아닌)
    "파이썬 버전",
    "python 버전",
    "git ",
    "리스트 정렬",
    "딕셔너리 ",
    "dictionary ",
    "for 문",
    "while 문",
    # 요리/생활
    "요리",
    "레시피",
    "운동",
    "다이어트",
    "영화",
    "드라마",
    "게임",
    "여행",
    # 사담
    "안녕",
    "반가",
    "고마워",
    "잘 지내",
    "심심",
)

# FINANCE 판정 보강: 아래 키워드 하나라도 있으면 무조건 FINANCE
_FINANCE_STRONG_KEYWORDS: tuple[str, ...] = (
    # 종목/회사 시그널
    "주식",
    "주가",
    "종목",
    "상장",
    "코스피",
    "코스닥",
    "KOSPI",
    "KOSDAQ",
    "NASDAQ",
    "NYSE",
    "SP500",
    "S&P",
    # 재무
    "매출",
    "영업이익",
    "순이익",
    "당기순이익",
    "EPS",
    "BPS",
    "부채",
    "자본",
    "자산",
    "재무",
    "재무제표",
    "실적",
    "분기",
    "연간",
    "ROE",
    "ROA",
    "ROIC",
    "마진",
    "이익률",
    "OCF",
    "FCF",
    "배당",
    "자사주",
    "CAPEX",
    "WACC",
    "DCF",
    "PER",
    "PBR",
    # 경제/매크로
    "경제",
    "경기",
    "사이클",
    "금리",
    "물가",
    "인플레",
    "환율",
    "유가",
    "매크로",
    "시황",
    "시장",
    "업황",
    "업종",
    "지수",
    "GDP",
    "CPI",
    "PPI",
    # 공시/분석
    "공시",
    "DART",
    "EDGAR",
    "SEC",
    "리포트",
    "보고서",
    "분석",
    "신용등급",
    "가치평가",
    "밸류에이션",
    "적정가",
    "목표가",
    # Intent keyword 전부 (위 _KEYWORDS 합집합의 핵심 일부)
    "수익성",
    "성장성",
    "안정성",
    "현금흐름",
    "전망",
    "예측",
    "비교",
    "랭킹",
    # 대표 종목명
    "삼성전자",
    "삼성",
    "LG전자",
    "SK하이닉스",
    "현대차",
    "현대자동차",
    "네이버",
    "카카오",
    "포스코",
    "애플",
    "Apple",
    "구글",
    "테슬라",
    "엔비디아",
    "Nvidia",
)


def classifyCategory(question: str, *, stockCode: str | None = None) -> Category:
    """질문 → META / FINANCE / OUT_OF_SCOPE.

    결정 트리:
    1. stockCode 힌트 있으면 즉시 FINANCE (UI/CLI 가 종목 지정)
    2. META 키워드 매칭 + 금융 강키워드 0개 → META
    3. OUT_OF_SCOPE 일반 주제 + 금융 강키워드 0개 → OUT_OF_SCOPE
    4. 나머지 → FINANCE (기본값, 모호하면 경유 강제)

    Args:
        question: 사용자 질문
        stockCode: UI/CLI 가 전달한 종목코드 힌트 (있으면 FINANCE 확정)
    """
    if stockCode:
        return Category.FINANCE

    if not question or not question.strip():
        return Category.FINANCE  # 빈 질문은 fallback — tool 경유로 유도

    q = question.lower()
    has_meta = any(kw.lower() in q for kw in _META_KEYWORDS)

    # META 먼저 — "dartlab 어떻게 쓰" 같은 질문은 "DART" substring 이
    # finance 키워드로 잘못 잡힐 수 있어 META 를 우선 확정.
    # 단, 회사 분석 맥락 ("삼성전자 dartlab 으로 분석") 같은 케이스는
    # 강한 finance 키워드가 있으면 FINANCE 로 복귀.
    has_finance_explicit = any(
        kw.lower() in q
        for kw in _FINANCE_STRONG_KEYWORDS
        if kw not in ("DART", "DartLab", "dartlab")  # dartlab/DART 는 META 방지
    )
    if has_meta and not has_finance_explicit:
        return Category.META

    # OUT_OF_SCOPE: 일반 주제 키워드 + 금융 신호 없음
    has_general = any(kw.lower() in q for kw in _GENERAL_TOPIC_KEYWORDS)
    if has_general and not has_finance_explicit:
        return Category.OUT_OF_SCOPE

    # 기본값 — 모호하면 FINANCE (경유 강제)
    return Category.FINANCE
