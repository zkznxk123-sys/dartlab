"""Asness-Frazzini-Pedersen QMJ 횡단면 quant factor.

학술: Asness, Frazzini, Pedersen (2019, Review of Accounting Studies) — Quality minus Junk.
     Q = (Profitability + Growth + Safety + Payout) / 4

dartlab 단순화 (단년도 data 기준):
    Profitability : (ROE_rank + ROA_rank + CFOA_rank) / 3
        ROE  = NI / Equity
        ROA  = NI / TA
        CFOA = OCF / TA
    Safety        : (1 − debtRatio_rank) = 저레버리지 선호
        debtRatio = TL / TA
    (Growth/Payout 생략 — 5y 시계열 / 배당 데이터 별도)

Q = 0.7 · Profitability + 0.3 · Safety

KR 2025 검증 완료 : RMW Sharpe +3.74 (factorBuild)
QMJ composite 는 profitability 핵심 축에 safety 10% 편입한 보수 안정판.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.core.finance.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import extract_account, load_scan_parquet
from dartlab.quant.factorBuild import _latest_year

log = logging.getLogger(__name__)


def _rank(values: list[float]) -> list[float]:
    arr = np.asarray(values, dtype=np.float64)
    order = arr.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(len(arr))
    return list(ranks / max(len(arr) - 1, 1))


def calcQMJ(
    *,
    market: str = "KR",
    stockCode: str | None = None,
    **kwargs,
) -> dict | None:
    """Asness-Frazzini-Pedersen QMJ composite — 한국 시장 품질주 랭킹.

    Capabilities:
        - 전종목 Q-score (profitability + safety 합성)
        - Top 10 Quality / Bottom 10 Junk
        - RMW 단독 (+3.74) 위에 safety 편입한 저위험 quality 축

    AIContext:
        - Sprint 2 재무 알파 — FF5 RMW 의 robust 확장
        - story `qmjBlock` 시장분석 자동 호출

    Args:
        market: ``"KR"`` | ``"US"``. 기본 ``"KR"``.

    Returns:
        dict — market / year / universe / scores / components / topQuality / topJunk / interpretation
    """
    try:
        lf = load_scan_parquet("finance", market)
        if lf is None:
            return None
        snap = extractAnnualConsolidated(lf.collect())
        year = _latest_year(snap)
        if year is None:
            return None
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        log.warning("calcQMJ year 실패: %s", type(exc).__name__)
        return None

    edgar = isEdgarSchema(snap)
    year_col = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    cur = snap.filter(pl.col(year_col) == year_val)
    if cur.is_empty():
        return None

    rows = []
    # 성능 fix (G5): partition_by 한 번 호출 → O(n) lookup
    partitions = cur.partition_by("stockCode", as_dict=True)
    for code_key, stock in partitions.items():
        code = code_key[0] if isinstance(code_key, tuple) else code_key
        if not isinstance(code, str) or stock.is_empty():
            continue
        ni = extract_account(stock, "net_income")
        eq = extract_account(stock, "total_equity")
        ta = extract_account(stock, "total_assets")
        tl = extract_account(stock, "total_liabilities")
        ocf = extract_account(stock, "operating_cf")
        if not ta or ta <= 0 or not eq or eq <= 0 or tl is None:
            continue
        roe = ni / eq if ni is not None else None
        roa = ni / ta if ni is not None else None
        cfoa = ocf / ta if ocf is not None else None
        debt_ratio = tl / ta
        if roe is None or roa is None or cfoa is None:
            continue
        rows.append(
            {
                "code": code,
                "roe": roe,
                "roa": roa,
                "cfoa": cfoa,
                "debtRatio": debt_ratio,
            }
        )

    if len(rows) < 50:
        return None

    roe_r = _rank([r["roe"] for r in rows])
    roa_r = _rank([r["roa"] for r in rows])
    cfoa_r = _rank([r["cfoa"] for r in rows])
    safety_r = _rank([-r["debtRatio"] for r in rows])  # 낮을수록 좋음

    scores = {}
    components = {}
    for i, r in enumerate(rows):
        prof = (roe_r[i] + roa_r[i] + cfoa_r[i]) / 3
        q = 0.7 * prof + 0.3 * safety_r[i]
        scores[r["code"]] = q
        components[r["code"]] = {
            "roe": round(r["roe"], 4),
            "roa": round(r["roa"], 4),
            "cfoa": round(r["cfoa"], 4),
            "debtRatio": round(r["debtRatio"], 4),
            "profScore": round(prof, 3),
            "safetyScore": round(safety_r[i], 3),
        }

    sorted_items = sorted(scores.items(), key=lambda x: -x[1])
    topQuality = [(c, round(s, 3)) for c, s in sorted_items[:10]]
    topJunk = [(c, round(s, 3)) for c, s in sorted_items[-10:]]

    total = len(scores)
    # 단일 종목 분기 (Step 6)
    if stockCode:
        s = scores.get(stockCode)
        if s is None:
            return {
                "stockCode": stockCode,
                "market": market,
                "year": str(year),
                "error": f"{stockCode} 데이터 없음 (universe {total}개 중 미포함)",
            }
        return {
            "stockCode": stockCode,
            "market": market,
            "year": str(year),
            "score": round(s, 3),
            "percentile": round(100 * s, 1),
            "components": components.get(stockCode, {}),
            "universe": total,
            "interpretation": (
                f"{stockCode} QMJ={round(s, 3)} (백분위 {round(100 * s, 0):.0f}) — Asness Profitability + Safety 합성."
            ),
        }

    return {
        "market": market,
        "year": str(year),
        "universe": total,
        "scores": {c: round(s, 3) for c, s in scores.items()},
        "components": components,
        "topQuality": topQuality,
        "topJunk": topJunk,
        "interpretation": (
            f"{market} {year}년 QMJ composite ({total}종목) — "
            "고 ROE/ROA/CFOA + 저 leverage 조합이 Asness QMJ premium 후보."
        ),
    }
