"""본 세션의 누적 의도·관심 추출 — history 결정론적 분석.

매 turn LLM 호출 없이 *통계만* — runAgent 의 history list 받아서 본 세션에서
사용자가 어떤 종목·토픽을 언급했는지, 어떤 발화 패턴인지 추출.

산출은 buildUserContextBlock 의 *현재 세션* 절반. userProfile (장기 누적) 과
짝지어 dialectic synthesis.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from .userProfile import _KO_STOPWORDS, _KO_TOKEN_RE, _KR_FALSE_TICKER, _KR_STOCKCODE_RE, _US_TICKER_RE

# 발화 의도 분류 휴리스틱 — 키워드 매칭 (LLM 호출 없음)
_INTENT_ANALYSIS = re.compile(r"분석|살펴|보여|찾아|랭킹|비교|어때|어떻|평가")
_INTENT_META = re.compile(r"규칙|룰|메모리|메모|설정|환경|뭐\s*할|능력")
_INTENT_VERIFY = re.compile(r"검증|작동|되나|확인|테스트|실측|진짜")
_INTENT_ACTION = re.compile(r"해봐|진행|박|만들|추가|구현|박는|수정")
_INTENT_DISCUSS = re.compile(r"왜|어째서|어떻게|뭐냐|뭐라|의미")


@dataclass
class SessionIntent:
    """본 세션의 의도·관심 추출 결과."""

    turn_count: int
    last_user_text_preview: str = ""
    intent_hint: str = "general"
    session_stock_codes: list[tuple[str, int]] = field(default_factory=list)
    session_tickers: list[tuple[str, int]] = field(default_factory=list)
    session_tokens: list[tuple[str, int]] = field(default_factory=list)


def _classifyIntent(text: str) -> str:
    """간단 패턴 매칭 — 더 강한 신호 우선 (action/verify > analysis > meta/discuss)."""
    if _INTENT_ACTION.search(text):
        return "action"
    if _INTENT_VERIFY.search(text):
        return "verify"
    if _INTENT_ANALYSIS.search(text):
        return "analysis"
    if _INTENT_META.search(text):
        return "meta"
    if _INTENT_DISCUSS.search(text):
        return "discuss"
    return "general"


def sessionIntent(history: list[dict[str, Any]], *, topN: int = 8) -> SessionIntent:
    """history list → 본 세션 의도·관심 추출.

    Args:
        history: [{"role": "user"|"assistant", "content": "..."}, ...] 형식.
            agent.runAgent 가 받는 history 와 동일 구조.
        topN: 종목·티커·토큰 top-N.

    Returns:
        SessionIntent. history 비었으면 turn_count=0 빈 객체.
    """
    if not history:
        return SessionIntent(turn_count=0)

    user_texts: list[str] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        if entry.get("role") != "user":
            continue
        content = entry.get("content") or entry.get("text") or ""
        if isinstance(content, str) and content.strip():
            user_texts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    t = block.get("text") or ""
                    if isinstance(t, str) and t.strip():
                        user_texts.append(t)

    if not user_texts:
        return SessionIntent(turn_count=0)

    stock_counts: Counter[str] = Counter()
    ticker_counts: Counter[str] = Counter()
    token_counts: Counter[str] = Counter()
    for text in user_texts:
        for m in _KR_STOCKCODE_RE.findall(text):
            stock_counts[m] += 1
        for m in _US_TICKER_RE.findall(text):
            if m in _KR_FALSE_TICKER:
                continue
            ticker_counts[m] += 1
        for tok in _KO_TOKEN_RE.findall(text):
            if tok in _KO_STOPWORDS:
                continue
            token_counts[tok] += 1

    last_text = user_texts[-1]
    return SessionIntent(
        turn_count=len(user_texts),
        last_user_text_preview=last_text[:120],
        intent_hint=_classifyIntent(last_text),
        session_stock_codes=stock_counts.most_common(topN),
        session_tickers=ticker_counts.most_common(topN),
        session_tokens=token_counts.most_common(topN),
    )


__all__ = ["SessionIntent", "sessionIntent"]
