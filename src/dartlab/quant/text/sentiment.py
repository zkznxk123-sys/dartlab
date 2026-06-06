"""공시 텍스트 감성 분석 — Loughran-McDonald 사전 기반.

학술 근거: Loughran & McDonald (2011).
"""

from __future__ import annotations

import logging

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import loadPanelTextForStock

log = logging.getLogger(__name__)


def calcSentiment(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """공시 텍스트 감성 스코어링.

    Loughran-McDonald 한국어 사전으로 공시 텍스트의 긍정·부정·불확실 단어를
    집계하고 감성 점수를 산출한다.

    Parameters
    ----------
    stockCode : str
        종목코드.
    market : str
        "KR" | "US" | "auto". 기본 "auto".

    Returns
    -------
    dict
        stockCode : str — 종목코드
        market : str — 시장
        sentimentScore : float — 종합 감성 점수 (-1~1, 점)
        positiveCount : int — 긍정 단어 수
        negativeCount : int — 부정 단어 수
        uncertaintyCount : int — 불확실 단어 수
        totalWords : int — 전체 단어 수
        positiveRatio : float — 긍정 비율 (비율)
        negativeRatio : float — 부정 비율 (비율)
        topNegativeWords : list[dict] — 부정 단어 빈도 상위 10개
            word : str, count : int
        timeSeries : list[dict] — 기간별 감성 점수 (최근 20개)
            period : str, score : float, pos : int, neg : int, words : int
        sentimentVerdict : str — "positive" | "negative" | "neutral"

    Capabilities:
        - 공시 본문 토큰화 → Loughran-McDonald 한국어 사전 매칭 → pos/neg/uncertainty 집계
        - 종합 점수 + verdict + top 부정 단어 + 시계열

    Guide:
        Loughran-McDonald 2011 금융 어휘 표준 + 한국어 사전 확장. score ≥ 0.1 = positive.

    When:
        Text alpha + AI 공시 톤 답변.

    How:
        ``loadPanelTextForStock`` → 토큰화 → 사전 매칭 → 통계 + 시계열.

    Requires:
        ``data/dart/panel/{stockCode}.parquet`` 가용.

    Raises:
        없음 — 텍스트 부재 시 ``{error}``.

    Example:
        >>> calcSentiment("005930")["sentimentVerdict"]
        'positive'

    See Also:
        - calcToneChange : 시계열 변화
        - calcRiskText : 위험 어휘
        - composite.calcTextComposite : 텍스트 통합

    AIContext:
        "공시 톤" 답변 시 sentimentScore + topNegativeWords 인용.
    """
    market = resolveMarket(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    panelText = loadPanelTextForStock(stockCode)
    if isEmptyDf(panelText):
        return {**result, "error": "panel 데이터 없음"}

    from dartlab.quant.text.lmDict import NEGATIVE_KR, POSITIVE_KR, UNCERTAINTY_KR

    text_col = next((c for c in ["content", "section_content", "text", "body"] if c in panelText.columns), None)
    if text_col is None:
        return {**result, "error": "텍스트 컬럼 없음", "columns": panelText.columns}

    period_col = next((c for c in ["period", "bsns_year", "year", "rcept_dt"] if c in panelText.columns), None)

    scores = []
    total_pos = total_neg = total_unc = total_words = 0
    neg_counts: dict[str, int] = {}

    texts = panelText.get_column(text_col).to_list()
    periods = panelText.get_column(period_col).to_list() if period_col else [None] * len(texts)

    for text, period in zip(texts, periods):
        if not isinstance(text, str) or not text.strip():
            continue
        words = text.split()
        nw = len(words)
        if nw == 0:
            continue

        pc = sum(1 for w in words if any(p in w for p in POSITIVE_KR))
        nc = sum(1 for w in words if any(n in w for n in NEGATIVE_KR))
        uc = sum(1 for w in words if any(u in w for u in UNCERTAINTY_KR))

        for w in words:
            for kw in NEGATIVE_KR:
                if kw in w:
                    neg_counts[kw] = neg_counts.get(kw, 0) + 1

        sc = (pc - nc) / (pc + nc + 1)
        scores.append(
            {"period": str(period)[:10] if period else None, "score": round(sc, 4), "pos": pc, "neg": nc, "words": nw}
        )
        total_pos += pc
        total_neg += nc
        total_unc += uc
        total_words += nw

    if not scores:
        return {**result, "error": "분석 가능한 텍스트 없음"}

    overall = (total_pos - total_neg) / (total_pos + total_neg + 1)
    result["sentimentScore"] = round(float(overall), 4)
    result["positiveCount"] = total_pos
    result["negativeCount"] = total_neg
    result["uncertaintyCount"] = total_unc
    result["totalWords"] = total_words
    result["positiveRatio"] = round(total_pos / max(total_words, 1), 6)
    result["negativeRatio"] = round(total_neg / max(total_words, 1), 6)
    result["topNegativeWords"] = [
        {"word": w, "count": c} for w, c in sorted(neg_counts.items(), key=lambda x: -x[1])[:10]
    ]
    result["timeSeries"] = scores[-20:]
    result["sentimentVerdict"] = "positive" if overall > 0.1 else "negative" if overall < -0.1 else "neutral"
    return result
