"""Sloan Accruals Quality 횡단면 quant factor.

학술:
- Sloan (1996) The Accounting Review — TATA = (NI - CFO) / TA
- Dechow-Dichev (2002) — 발생액 품질 residual 척도

공식: Accrual = (Net Income - Operating Cash Flow) / Total Assets

해석:
    Accrual 높음 (> +5%) : 발생주의 이익 비중 큼 → 장래 reversal 가능성 (음의 alpha)
    Accrual 낮음 (< -5%) : 현금 중심 이익 → 장래 positive alpha

Sloan (1996): 상위 accrual 분위 − 하위 분위 long-short 가 연 10% alpha (미국 1962~1991).
dartlab 데이터: DART finance.parquet (NI + CFO + TA). 단년도.
"""

from __future__ import annotations

import logging

import polars as pl

from dartlab.core.cross.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant._helpers import extractAccount, loadScanParquet
from dartlab.quant.factorBuild import _latest_year

log = logging.getLogger(__name__)


def calcAccrualsFactor(
    *,
    market: str = "KR",
    stockCode: str | None = None,
    **kwargs,
) -> dict | None:
    """Sloan Accruals 횡단면 quant factor — 한국 시장 이익 품질 지도.

    Capabilities:
        - 전종목 Accrual = (NI - CFO) / TA 횡단면 분포
        - 3 그룹 (high/neutral/low) 분포
        - Sloan long-short 후보 (low − high) universe

    AIContext:
        - Sprint 2 재무 알파 — 이익 품질 필터
        - accrual 높은 종목 = 장래 실적 실망 risk
        - story `accrualsFactorBlock` 시장분석 자동 호출

    Guide:
        - 시장 스냅샷 : calcAccrualsFactor()

    SeeAlso:
        - calcBeneishFactor : 이익 조작 (보완)
        - calcPiotroskiFactor : 건강 (F4 cfGtNi 가 같은 원리)

    Args:
        market: ``"KR"`` | ``"US"``. 기본 ``"KR"``.

    Returns:
        dict
            market : str
            year : str
            universe : int
            scores : dict[str, float] — {stockCode: accrual ratio (%)}
            groups : dict — {high: {count, pct}, neutral: {...}, low: {...}}
            topHigh : list[tuple[str, float]] — 고 accrual (음의 alpha 후보)
            topLow : list[tuple[str, float]] — 저 accrual (양의 alpha 후보)
            interpretation : str
    """
    try:
        lf = loadScanParquet("finance", market)
        if lf is None:
            return None
        snap = extractAnnualConsolidated(lf.collect())
        year = _latest_year(snap)
        if year is None:
            return None
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        log.warning("calcAccrualsFactor year 실패: %s", type(exc).__name__)
        return None

    edgar = isEdgarSchema(snap)
    year_col = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    cur = snap.filter(pl.col(year_col) == year_val)
    if cur.is_empty():
        return None

    scores: dict[str, float] = {}
    # 성능 fix (G5): partition_by 한 번 호출 → O(n) lookup
    partitions = cur.partition_by("stockCode", as_dict=True)
    for code_key, stock in partitions.items():
        code = code_key[0] if isinstance(code_key, tuple) else code_key
        if not isinstance(code, str) or stock.is_empty():
            continue
        ni = extractAccount(stock, "net_income")
        ocf = extractAccount(stock, "operating_cf")
        ta = extractAccount(stock, "total_assets")
        if ni is None or ocf is None or not ta or ta <= 0:
            continue
        accrual = ((ni - ocf) / ta) * 100
        scores[code] = accrual

    if not scores:
        return None

    groups_count = {"high": 0, "neutral": 0, "low": 0}
    for a in scores.values():
        if a > 5.0:
            groups_count["high"] += 1
        elif a < -5.0:
            groups_count["low"] += 1
        else:
            groups_count["neutral"] += 1
    total = len(scores)
    groups = {k: {"count": v, "pct": round(100 * v / total, 1)} for k, v in groups_count.items()}

    sorted_items = sorted(scores.items(), key=lambda x: -x[1])
    topHigh = [(c, round(a, 2)) for c, a in sorted_items[:10]]
    topLow = [(c, round(a, 2)) for c, a in sorted_items[-10:]]

    # 단일 종목 분기 (Step 6)
    if stockCode:
        a = scores.get(stockCode)
        if a is None:
            return {
                "stockCode": stockCode,
                "market": market,
                "year": str(year),
                "error": f"{stockCode} 데이터 없음 (universe {total}개 중 미포함)",
            }
        group = "high" if a > 5.0 else ("low" if a < -5.0 else "neutral")
        return {
            "stockCode": stockCode,
            "market": market,
            "year": str(year),
            "score": round(a, 2),
            "group": group,
            "universe": total,
            "interpretation": (
                f"{stockCode} Sloan Accrual={round(a, 2)}% ({group}) — "
                + (
                    "reversal risk (발생주의 이익 큼)."
                    if group == "high"
                    else "cash quality premium 후보 (현금 중심)."
                    if group == "low"
                    else "중립."
                )
            ),
        }

    return {
        "market": market,
        "year": str(year),
        "universe": total,
        "scores": {c: round(a, 2) for c, a in scores.items()},
        "groups": groups,
        "topHigh": topHigh,
        "topLow": topLow,
        "interpretation": (
            f"{market} {year}년 {total}개 종목 Accrual 분포: "
            f"high {groups['high']['pct']}% (reversal risk), "
            f"low {groups['low']['pct']}% (cash quality premium 후보)."
        ),
    }
