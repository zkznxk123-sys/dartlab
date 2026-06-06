"""리스크 텍스트 델타 — 리스크 팩터 출현/소멸 추적.

학술 근거: Campbell et al. (2014) — Information Content of Mandatory Risk Factor Disclosures.
"""

from __future__ import annotations

import logging

from dartlab.core.market import resolveMarket
from dartlab.core.polarsUtil import isEmptyDf
from dartlab.quant.screen.dataAccess import loadPanelTextForStock

log = logging.getLogger(__name__)

_RISK_KEYWORDS = {
    "위험",
    "리스크",
    "불확실",
    "소송",
    "분쟁",
    "제재",
    "우발",
    "충당",
    "손상",
    "감액",
    "부실",
    "부도",
    "파산",
    "유동성위기",
    "채무불이행",
    "횡령",
    "배임",
    "과징금",
    "제소",
    "손해배상",
}


def calcRiskText(stockCode: str, *, market: str = "auto", **kwargs) -> dict:
    """리스크 팩터 텍스트 델타 분석.

    공시 문서에서 리스크 키워드(위험·소송·부도 등) 출현 빈도를 집계하고,
    기간별 추세·신규 리스크·밀도 기반 리스크 등급을 산출한다.

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
        totalMentions : int — 전체 리스크 키워드 출현 횟수
        riskTimeSeries : list[dict] — 기간별 멘션 수·키워드 목록 (최근 10개)
        trend : str — "increasing" | "decreasing" | "stable" | "insufficient_data"
        newRisks : list[str] — 최근 기간에 새로 등장한 키워드
        riskScore : float — 멘션 밀도 (천 단어당, 점)
        riskGrade : str — "high" | "medium" | "low"

    Capabilities:
        - 리스크 키워드 (위험/소송/부도/제소 등) 출현 + 기간별 추세 + 신규 키워드 식별
        - 멘션 밀도 (1000 단어당) → riskGrade 분류

    Guide:
        Loughran-McDonald risk-related 어휘 확장. 신규 등장 키워드는 "이번 분기 추가된 위험".

    When:
        Text 위험 + AI 공시 위험 경고 답변.

    How:
        ``loadPanelTextForStock`` → 키워드 매칭 → 기간별 카운트 + 추세.

    Requires:
        panel text 데이터 가용.

    Raises:
        없음 — 데이터 부재 시 ``{error}``.

    Example:
        >>> calcRiskText("005930")["riskGrade"]
        'medium'

    See Also:
        - calcSentiment / calcToneChange : 자매 text 축
        - composite.calcTextComposite : 통합

    AIContext:
        "공시 위험 어휘 증가" 답변 시 trend + newRisks 인용.
    """
    market = resolveMarket(stockCode, market)
    result: dict = {"stockCode": stockCode, "market": market}

    panelText = loadPanelTextForStock(stockCode)
    if isEmptyDf(panelText):
        return {**result, "error": "panel 데이터 없음"}

    text_col = next((c for c in ["content", "section_content", "text", "body"] if c in panelText.columns), None)
    if text_col is None:
        return {**result, "error": "텍스트 컬럼 없음"}

    period_col = next((c for c in ["period", "bsns_year", "year", "rcept_dt"] if c in panelText.columns), None)

    # 기간별 리스크 키워드 집계
    period_risks: dict[str, dict[str, int]] = {}
    texts = panelText.get_column(text_col).to_list()
    periods = panelText.get_column(period_col).to_list() if period_col else [str(i) for i in range(len(texts))]

    total_mentions = 0
    for text, period in zip(texts, periods):
        if not isinstance(text, str):
            continue
        pkey = str(period)[:10] if period else "unknown"
        if pkey not in period_risks:
            period_risks[pkey] = {}
        for kw in _RISK_KEYWORDS:
            count = text.count(kw)
            if count > 0:
                period_risks[pkey][kw] = period_risks[pkey].get(kw, 0) + count
                total_mentions += count

    if not period_risks:
        return {**result, "error": "리스크 키워드 없음"}

    sorted_periods = sorted(period_risks.keys())
    # 기간별 총 멘션 수
    ts = [
        {"period": p, "mentions": sum(period_risks[p].values()), "keywords": list(period_risks[p].keys())}
        for p in sorted_periods
    ]

    result["totalMentions"] = total_mentions
    result["riskTimeSeries"] = ts[-10:]

    # 추세 감지
    if len(ts) >= 3:
        counts = [t["mentions"] for t in ts]
        recent_avg = sum(counts[-2:]) / 2
        older_avg = sum(counts[:-2]) / max(len(counts) - 2, 1)
        if recent_avg > older_avg * 1.3:
            result["trend"] = "increasing"
        elif recent_avg < older_avg * 0.7:
            result["trend"] = "decreasing"
        else:
            result["trend"] = "stable"
    else:
        result["trend"] = "insufficient_data"

    # 신규 리스크: 최근에만 등장, 이전에 없던 키워드
    if len(sorted_periods) >= 2:
        latest_kw = set(period_risks[sorted_periods[-1]].keys())
        older_kw = set()
        for p in sorted_periods[:-1]:
            older_kw.update(period_risks[p].keys())
        new_risks = latest_kw - older_kw
        result["newRisks"] = list(new_risks)
    else:
        result["newRisks"] = []

    # 리스크 점수 (멘션 밀도 기반)
    total_words = sum(len(t.split()) for t in texts if isinstance(t, str))
    risk_density = total_mentions / max(total_words, 1) * 1000
    result["riskScore"] = round(risk_density, 4)
    result["riskGrade"] = "high" if risk_density > 5 else "medium" if risk_density > 2 else "low"
    return result
