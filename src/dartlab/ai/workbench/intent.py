"""Intent 분기 + 정규식·키워드 SSOT.

질문이 *분석 의도* 인지 판정. 그 외엔 LLM 본체 (chatNative) 가 처리.
다른 모듈 (targets, heuristic) 은 본 모듈의 정규식·키워드 상수를 재사용한다.
"""

from __future__ import annotations

import re
from typing import Any

# 정규식 — 질문에서 종목코드 / 티커 / 회사 분리 / show 주제 인식.
_COMPANY_SPLIT_RE = re.compile(r"\s*(?:,|/|vs\.?|VS\.?|랑|하고|와|과)\s*")
_STOCK_CODE_RE = re.compile(r"\b\d{6}\b")
_TICKER_RE = re.compile(r"\b[A-Z]{1,5}\b")

_SHOW_TOPIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("BS", ("BS", "balance sheet", "재무상태표", "재무제표", "자산", "부채", "자본")),
    ("IS", ("IS", "income statement", "손익계산서", "손익", "이익", "매출")),
    ("CF", ("CF", "cash flow", "현금흐름표", "현금흐름", "FCF", "free cash flow")),
)

_ACTION_WORDS = (
    "확인",
    "비교",
    "분석",
    "설명",
    "계산",
    "알려줘",
    "해줘",
    "봐줘",
    "찾아줘",
    "재무제표",
    "재무상태표",
    "손익계산서",
    "현금흐름표",
    "자산",
    "부채",
    "자본",
)

# 분석 의도 신호 — chat-native 와 5 패스 분기 키워드.
# 종목코드 (6 자리) / stockCode kwargs / 명시적 모드 외, 아래 키워드가 질문 안에 등장하면 분석.
# 그 외엔 LLM 본체 (chat-native) 가 답한다.
_ANALYSIS_INTENT_KEYWORDS = (
    "분석",
    "재무제표",
    "재무상태표",
    "손익계산서",
    "현금흐름표",
    "재무비율",
    "수익성",
    "안정성",
    "성장성",
    "밸류에이션",
    "공시",
    "랭킹",
    "스캔",
    "scan",
    "valuation",
    "ratios",
    "DCF",
    "EBITDA",
    "FCF",
    "PER",
    "PBR",
    "ROE",
    "ROA",
    "EPS",
    "BPS",
)


def isAnalysisIntent(question: str, kwargs: dict[str, Any]) -> bool:
    """질문이 분석 의도인지 판정. 그 외엔 LLM 본체 (chat-native) 가 처리.

    True 조건:
    - kwargs.stockCode 가 명시됨 (UI workspaceContext.company)
    - 질문 안에 6 자리 종목코드 (\\d{6})
    - 분석 키워드 1 개 이상 매치 (한국어/영어 케이스 무관)
    """
    if kwargs.get("stockCode"):
        return True
    text = str(question or "")
    if _STOCK_CODE_RE.search(text):
        return True
    lowered = text.lower()
    for kw in _ANALYSIS_INTENT_KEYWORDS:
        if kw.lower() in lowered:
            return True
    return False
