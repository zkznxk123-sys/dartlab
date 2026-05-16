"""credit/engine.py 의 5 스코어 헬퍼 — evaluateCompany 가 호출.

_scoreCashFlow / _scoreBusinessStability / _scoreReliability / _scoreDisclosureRisk /
_calcHistoricalScores — 신용 7 축 중 4~7 축 + 시계열 과거 점수 산출. evaluateCompany 의
god module 분리 일환.

각 함수는 latest dict 또는 sub-dict 를 받아 (지표명, 위험점수 0~100) tuple 리스트 반환.
값 None 이면 해당 지표 평가 누락.
"""

from __future__ import annotations

from dartlab.credit.scoring.creditScorecard import scoreMetric

# ═══════════════════════════════════════════════════════════


def _scoreCashFlow(latest: dict, metrics: dict) -> list[tuple[str, float | None]]:
    """축 4: 현금흐름 점수."""
    scores = []

    ocfSales = latest.get("ocfToSales")
    if ocfSales is not None:
        if ocfSales > 20:
            scores.append(("OCF/매출", 0.0))
        elif ocfSales > 10:
            scores.append(("OCF/매출", 10.0))
        elif ocfSales > 5:
            scores.append(("OCF/매출", 20.0))
        elif ocfSales > 0:
            scores.append(("OCF/매출", 35.0))
        else:
            scores.append(("OCF/매출", min(70, 50 + abs(ocfSales))))

    fcfSales = latest.get("fcfToSales")
    if fcfSales is not None:
        if fcfSales > 10:
            scores.append(("FCF/매출", 0.0))
        elif fcfSales > 0:
            scores.append(("FCF/매출", 15.0))
        else:
            scores.append(("FCF/매출", min(60, 35 + abs(fcfSales))))

    # OCF 추세 (3기 연속 양수이면 안정)
    ocfs = [h.get("ocf") for h in metrics["history"][:3]]
    validOcfs = [o for o in ocfs if o is not None]
    if len(validOcfs) >= 3:
        if all(o > 0 for o in validOcfs):
            scores.append(("OCF추세", 0.0))
        elif validOcfs[0] is not None and validOcfs[0] < 0:
            scores.append(("OCF추세", 50.0))
        else:
            scores.append(("OCF추세", 20.0))

    return scores


def _scoreBusinessStability(biz: dict) -> list[tuple[str, float | None]]:
    """축 5: 사업 안정성 점수."""
    scores = []

    revCV = biz.get("revenueCV")
    if revCV is not None:
        if revCV < 5:
            scores.append(("매출안정성", 0.0))
        elif revCV < 15:
            scores.append(("매출안정성", (revCV - 5) * 2))
        elif revCV < 30:
            scores.append(("매출안정성", 20 + (revCV - 15) * 1.5))
        else:
            scores.append(("매출안정성", min(55, 42.5 + (revCV - 30) * 0.5)))

    opCV = biz.get("opMarginCV")
    if opCV is not None:
        if opCV < 10:
            scores.append(("이익안정성", 0.0))
        elif opCV < 30:
            scores.append(("이익안정성", (opCV - 10)))
        elif opCV < 60:
            scores.append(("이익안정성", 20 + (opCV - 30) * 0.5))
        else:
            scores.append(("이익안정성", min(50, 35)))

    latestRev = biz.get("latestRevenue")
    if latestRev is not None:
        revTril = latestRev / 1e12
        if revTril > 50:
            scores.append(("규모", 0.0))
        elif revTril > 10:
            scores.append(("규모", 5.0))
        elif revTril > 1:
            scores.append(("규모", 15.0))
        elif revTril > 0.1:
            scores.append(("규모", 30.0))
        else:
            scores.append(("규모", 45.0))

    hhi = biz.get("segmentHHI")
    if hhi is not None:
        if hhi < 1500:
            scores.append(("부문다각화", 0.0))
        elif hhi < 2500:
            scores.append(("부문다각화", 15.0))
        elif hhi < 5000:
            scores.append(("부문다각화", 30.0))
        else:
            scores.append(("부문다각화", 40.0))

    return scores


def _scoreReliability(rel: dict, auditOpinion: str | None) -> list[tuple[str, float | None]]:
    """축 6: 재무 신뢰성 점수."""
    scores = []

    # Beneish M-Score
    m = rel.get("beneishMScore")
    if m is not None:
        if m < -2.22:
            scores.append(("Beneish M", 0.0))
        elif m < -1.78:
            scores.append(("Beneish M", 20.0))
        else:
            scores.append(("Beneish M", 45.0))

    # Piotroski F-Score
    f = rel.get("piotroskiFScore")
    if f is not None:
        if f >= 7:
            scores.append(("Piotroski F", 0.0))
        elif f >= 5:
            scores.append(("Piotroski F", 10.0))
        elif f >= 3:
            scores.append(("Piotroski F", 25.0))
        else:
            scores.append(("Piotroski F", 45.0))

    # 감사의견
    if auditOpinion is not None:
        if "적정" in auditOpinion and "한정" not in auditOpinion and "부적정" not in auditOpinion:
            scores.append(("감사의견", 0.0))
        elif "한정" in auditOpinion:
            scores.append(("감사의견", 50.0))
        elif "부적정" in auditOpinion or "의견거절" in auditOpinion:
            scores.append(("감사의견", 90.0))

    return scores


def _scoreDisclosureRisk(dr: dict | None) -> list[tuple[str, float | None]]:
    """축 7: 공시 리스크 점수."""
    if dr is None:
        return []

    scores = []

    chronic = dr.get("chronicYears") or dr.get("chronic_years", 0)
    if chronic >= 3:
        scores.append(("우발부채만성", 60.0))
    elif chronic >= 1:
        scores.append(("우발부채만성", 25.0))
    else:
        scores.append(("우발부채만성", 0.0))

    risk = dr.get("riskKeyword") or dr.get("risk_keyword", 0)
    if risk > 0:
        scores.append(("리스크키워드", min(70, 30 + risk * 10)))
    else:
        scores.append(("리스크키워드", 0.0))

    return scores


def _calcHistoricalScores(metrics: dict, thresholds: dict) -> list[float]:
    """과거 기간 간이 점수 (시계열 안정화용)."""
    scores = []
    for h in metrics["history"][1:3]:
        pScores = []
        for key, tKey in [
            ("ffoToDebt", "ffo_to_debt"),
            ("debtToEbitda", "debt_to_ebitda"),
            ("ebitdaInterestCoverage", "ebitda_interest_coverage"),
            ("debtRatio", "debt_ratio"),
            ("currentRatio", "current_ratio"),
        ]:
            s = scoreMetric(h.get(key), thresholds[tKey])
            if s is not None:
                pScores.append(s)
        if pScores:
            scores.append(round(sum(pScores) / len(pScores), 2))
    return scores


__all__ = [
    "_calcHistoricalScores",
    "_scoreBusinessStability",
    "_scoreCashFlow",
    "_scoreDisclosureRisk",
    "_scoreReliability",
]
