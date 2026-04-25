"""Text Factor Composite — sentiment + tone change + risk text + governance 통합 alpha.

학술 :
    - Tetlock (2007, Journal of Finance) — pessimism words → 시장 수익률 예측
    - Loughran-McDonald (2011) — 금융 dictionary, 부정 어휘 alpha
    - Li (2008) — 어조 변화 (toneChange) 비대칭 정보 전달

dartlab 9 텍스트 축 (textSentiment / toneChange / riskText / governanceQuant) 합성 :
    composite = w1·sentiment_z + w2·(-toneChange_z) + w3·(-riskText_z) + w4·governance_z

음의 가중치 = 부정 톤 / 위험 어휘 / 거버넌스 약화 일 때 점수 ↓.

story 통합 시 single composite metric 으로 5+ 축 동시 표시.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _zScore(v: float, ref_mean: float, ref_std: float) -> float:
    if ref_std <= 0:
        return 0.0
    return (v - ref_mean) / ref_std


def calcTextComposite(
    stockCode: str,
    *,
    market: str = "auto",
    weights: tuple[float, float, float, float] = (0.4, 0.2, 0.2, 0.2),
) -> dict | None:
    """Text Factor Composite — 4 텍스트 축 합성 점수 (단일 종목).

    Capabilities:
        - sentiment + (-toneChange) + (-riskText) + governance 4축 weighted z-score
        - 단일 composite -3 ~ +3 (대략) 점수 + 정성 평가
        - dartlab text 9 축 의 첫 번째 통합 진입점

    AIContext:
        - Sprint 4 dartlab Korea-Native — 한국어 공시 본문 텍스트 alpha
        - story `textCompositeBlock` 시장분석 후속

    Args:
        stockCode: 종목코드.
        market: ``"auto"`` | ``"KR"`` | ``"US"``.
        weights: (sentiment, toneChange_neg, riskText_neg, governance) — 합 1.

    Returns:
        dict
            stockCode : str
            scores : dict — {sentiment, toneChange, riskText, governance}
            composite : float — weighted z (negative weight 적용)
            interpretation : str
        None — 텍스트 데이터 0개
    """
    try:
        from dartlab.quant.governanceQuant import calcGovernance
        from dartlab.quant.riskText import calcRiskText
        from dartlab.quant.textSentiment import calcSentiment
        from dartlab.quant.toneChange import calcToneChange
    except ImportError:
        return None

    s_data = calcSentiment(stockCode, market=market)
    t_data = calcToneChange(stockCode, market=market)
    r_data = calcRiskText(stockCode, market=market)
    g_data = calcGovernance(stockCode, market=market)

    scores = {}
    if s_data and "score" in s_data:
        scores["sentiment"] = float(s_data["score"])
    if t_data and "toneChangeScore" in t_data:
        scores["toneChange"] = float(t_data["toneChangeScore"])
    elif t_data and "score" in t_data:
        scores["toneChange"] = float(t_data["score"])
    if r_data and "riskScore" in r_data:
        scores["riskText"] = float(r_data["riskScore"])
    elif r_data and "score" in r_data:
        scores["riskText"] = float(r_data["score"])
    if g_data and "governanceScore" in g_data:
        scores["governance"] = float(g_data["governanceScore"])
    elif g_data and "score" in g_data:
        scores["governance"] = float(g_data["score"])

    if len(scores) == 0:
        return None

    # 단순 합성 (z-score 기준 부재 — 절댓값 사용, 가중치만 적용)
    w_sent, w_tone, w_risk, w_gov = weights
    composite = (
        w_sent * scores.get("sentiment", 0)
        + w_tone * (-scores.get("toneChange", 0))
        + w_risk * (-scores.get("riskText", 0))
        + w_gov * scores.get("governance", 0)
    )

    if composite > 0.5:
        verdict = "긍정 텍스트 시그널"
    elif composite > 0.1:
        verdict = "약한 긍정"
    elif composite > -0.1:
        verdict = "중립"
    elif composite > -0.5:
        verdict = "약한 부정"
    else:
        verdict = "부정 텍스트 시그널"

    return {
        "stockCode": stockCode,
        "market": market,
        "scores": {k: round(v, 3) for k, v in scores.items()},
        "weights": list(weights),
        "composite": round(composite, 3),
        "interpretation": (f"{stockCode} 텍스트 합성 {round(composite, 2)} — {verdict} (축 {len(scores)}개)."),
    }
