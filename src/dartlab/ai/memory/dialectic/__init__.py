"""Dialectic user model — *장기 interest profile* + *현재 세션 intent* 합성.

매 turn LLM 호출 없이 결정론적 통계만. agent.runAgent 진입부에서
buildUserContextBlock(history) 호출 → system prompt 부착 블록 반환.

honcho 변증법적 사용자 모델의 가벼운 버전 — 답변마다 사용자 *주요 관심* +
*이번 세션 의도* 가 context 에 흐른다.
"""

from __future__ import annotations

from typing import Any

from .feedbackSignals import FeedbackSignals, extractFeedbackSignals
from .sessionIntent import SessionIntent, sessionIntent
from .userProfile import UserProfile, userInterestProfile

_INTENT_KO = {
    "analysis": "분석 요청",
    "verify": "검증·작동 확인",
    "action": "행동 지시 (박기·진행·구현)",
    "meta": "메타·룰·메모리",
    "discuss": "의미·이유 토론",
    "general": "일반",
}


def buildUserContextBlock(
    history: list[dict[str, Any]] | None,
    *,
    forceRefresh: bool = False,
) -> str:
    """system prompt 부착용 사용자 컨텍스트 블록.

    Args:
        history: agent.runAgent 의 history list. None 또는 빈 list 도 허용.
        forceRefresh: True 면 profile 캐시 무시 재계산.

    Returns:
        markdown 블록. 데이터 부족 시 빈 문자열 (호출자 graceful skip).
    """
    profile = userInterestProfile(forceRefresh=forceRefresh)
    intent = sessionIntent(history or [])

    if profile.total_user_turns == 0 and intent.turn_count == 0:
        return ""

    lines: list[str] = ["## 사용자 컨텍스트 (메모리 + 세션 합성)"]

    # 영문 ticker 는 블록 출력에서 제외 — 한국 시장 중심 사용자 환경에서 false
    # positive 비율 (PASS / SKILL / SSOT 같은 기술 약어) 가 신호 대비 너무 크다.
    # 내부 통계 (UserProfile.top_tickers) 는 유지 — 미래 US 시장 활용 늘면 재노출.
    if profile.total_user_turns > 0:
        parts: list[str] = []
        if profile.top_stock_codes:
            sc = " · ".join(c for c, _ in profile.top_stock_codes[:5])
            parts.append(f"자주 보는 종목: {sc}")
        if profile.theme_breakdown:
            top_themes = sorted(profile.theme_breakdown.items(), key=lambda x: -x[1])[:5]
            tm = " · ".join(f"{name}({cnt})" for name, cnt in top_themes)
            parts.append(f"주요 테마: {tm}")
        if profile.top_ko_tokens:
            tk = " · ".join(t for t, _ in profile.top_ko_tokens[:6])
            parts.append(f"자주 쓰는 키워드: {tk}")
        if parts:
            lines.append(f"**누적 ({profile.total_user_turns} turns)**")
            for p in parts:
                lines.append(f"- {p}")

    if intent.turn_count > 0:
        intent_label = _INTENT_KO.get(intent.intent_hint, intent.intent_hint)
        session_lines: list[str] = [f"**이번 세션 ({intent.turn_count} turns, 의도: {intent_label})**"]
        if intent.session_stock_codes:
            sc = " · ".join(c for c, _ in intent.session_stock_codes[:3])
            session_lines.append(f"- 언급 종목: {sc}")
        if intent.session_tokens:
            tk = " · ".join(t for t, _ in intent.session_tokens[:6])
            session_lines.append(f"- 키워드: {tk}")
        if intent.last_user_text_preview:
            preview = intent.last_user_text_preview.replace("\n", " ").strip()[:100]
            session_lines.append(f'- 마지막 발화: "{preview}"')
        lines.extend(session_lines)

    lines.append("")
    lines.append(
        "위 컨텍스트는 사용자가 *명시한 적 없는 가정* 이 아니라 *누적 통계* 다. 답변 톤·우선순위를 본 신호에 맞춰라 — 자주 본 종목·테마·키워드 우선, 이번 세션 의도와 부합하게."
    )

    return "\n".join(lines) + "\n"


def buildFeedbackSignalsBlock(*, forceRefresh: bool = False) -> str:
    """사용자 피드백 시그널 블록 — 부정/긍정 발화 원문 직접 인용.

    LLM 이 *원문 맥락* 을 보고 회피·강화 패턴을 추론. 결정론 분류 X.

    Args:
        forceRefresh: True 면 캐시 무시 재추출.

    Returns:
        markdown 블록. 시그널 없으면 빈 문자열.
    """
    signals = extractFeedbackSignals(forceRefresh=forceRefresh)
    if not signals.negatives and not signals.positives:
        return ""

    lines: list[str] = ["## 사용자 피드백 시그널 (자기-학습 — 회피·강화)"]

    if signals.negatives:
        lines.append("**부정 발화 (회피 시그널 — 다음 답변에서 이런 반응 안 받게)**")
        for s in signals.negatives:
            preview = s.replace("\n", " ").strip()
            lines.append(f'  - "{preview}"')

    if signals.positives:
        lines.append("**긍정 발화 (강화 시그널 — 이런 답변 패턴 유지)**")
        for s in signals.positives:
            preview = s.replace("\n", " ").strip()
            lines.append(f'  - "{preview}"')

    lines.append("")
    lines.append(
        "위 발화 원문은 *최근 sessionIndex 검출* 사용자 발화 그대로다. 분류·해석 안 됨 — *맥락 추론* 으로 어떤 답변 패턴이 부정 발화 유도했는지 / 긍정 발화 유도했는지 직접 추론하고, 같은 회귀 차단·같은 강화 유지."
    )

    return "\n".join(lines) + "\n"


__all__ = [
    "FeedbackSignals",
    "SessionIntent",
    "UserProfile",
    "buildFeedbackSignalsBlock",
    "buildUserContextBlock",
    "extractFeedbackSignals",
    "sessionIntent",
    "userInterestProfile",
]
