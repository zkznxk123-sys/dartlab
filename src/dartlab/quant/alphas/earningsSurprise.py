"""PEAD (Post-Earnings Announcement Drift) 횡단면 quant factor.

학술: Bernard & Thomas (1989, Journal of Accounting and Economics) — 실적 발표 후
     긍정 서프라이즈 종목이 60~90일 drift 상승, 음의 서프라이즈가 drift 하락.
     Ball & Brown (1968) 최초 관측, Bernard-Thomas 가 정식 PEAD 팩터화.

dartlab 단순화 (forecast 없을 때 SUE = Standardized Unexpected Earnings):
    SUE = (NI_t − NI_{t-1}) / σ(NI)_rolling
    (t는 분기/연도)

단년도 annual data 면:
    growth = (NI_{y} − NI_{y-1}) / |NI_{y-1}|
    SUE = growth 의 시장 횡단면 z-score

Top 10 positive SUE = PEAD long 후보 (60~90일 홀드).
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.core.cross.scanBridge import extractAnnualConsolidated, isEdgarSchema
from dartlab.quant.factor.build import _latestYear
from dartlab.quant.screen.dataAccess import extractAccount, loadScanParquet

log = logging.getLogger(__name__)


def calcEarningsSurprise(
    *,
    market: str = "KR",
    stockCode: str | None = None,
    **kwargs,
) -> dict | None:
    """Earnings Surprise (SUE) — 한국 시장 PEAD drift 후보 랭킹.

    Capabilities:
        - 전종목 YoY 순이익 성장률 + 횡단면 z-score
        - Top 10 positive SUE (post-earnings drift long 후보)
        - Top 10 negative SUE (drift short 후보)
        - Bernard-Thomas 1989 PEAD

    AIContext:
        - Sprint 2 재무 알파 — 펀더멘털 서프라이즈 momentum
        - story `earningsSurpriseBlock` 시장분석 자동 호출

    Args:
        market: ``"KR"`` | ``"US"``. 기본 ``"KR"``.

    Returns:
        dict — market / year / prevYear / universe / scores / topPos / topNeg / interpretation
    """
    try:
        lf = loadScanParquet("finance", market)
        if lf is None:
            return None
        snap = extractAnnualConsolidated(lf.collect())
        year = _latestYear(snap)
        if year is None:
            return None
    except (OSError, ValueError, KeyError, AttributeError) as exc:
        log.warning("calcEarningsSurprise year 실패: %s", type(exc).__name__)
        return None

    edgar = isEdgarSchema(snap)
    yearCol = "fy" if edgar else "bsns_year"
    year_val = int(year) if edgar else year
    try:
        prev_year_val = int(year) - 1 if edgar else str(int(year) - 1)
    except ValueError:
        return None
    cur = snap.filter(pl.col(yearCol) == year_val)
    prev = snap.filter(pl.col(yearCol) == prev_year_val)
    if cur.is_empty() or prev.is_empty():
        return None

    growths: dict[str, float] = {}
    # 성능 fix (G5): partition_by 한 번 호출 → O(n) lookup
    cur_parts = cur.partition_by("stockCode", as_dict=True)
    prev_parts = prev.partition_by("stockCode", as_dict=True)
    for code_key, s_cur in cur_parts.items():
        code = code_key[0] if isinstance(code_key, tuple) else code_key
        if not isinstance(code, str):
            continue
        s_prev = prev_parts.get(code_key)
        if s_prev is None or s_prev.is_empty():
            continue
        ni = extractAccount(s_cur, "net_income")
        ni_p = extractAccount(s_prev, "net_income")
        if ni is None or ni_p is None or abs(ni_p) < 1:
            continue
        growth = (ni - ni_p) / abs(ni_p)
        # 극단 outlier 클램핑 (±500%)
        growth = max(-5.0, min(5.0, growth))
        growths[code] = growth

    if len(growths) < 50:
        return None

    vals = np.asarray(list(growths.values()))
    mean = float(vals.mean())
    std = float(vals.std(ddof=1))
    scores = {c: (g - mean) / std if std > 0 else 0.0 for c, g in growths.items()}

    sorted_items = sorted(scores.items(), key=lambda x: -x[1])
    topPos = [(c, round(s, 2), round(growths[c], 2)) for c, s in sorted_items[:10]]
    topNeg = [(c, round(s, 2), round(growths[c], 2)) for c, s in sorted_items[-10:]]

    total = len(scores)
    # 단일 종목 분기 (Step 6)
    if stockCode:
        z = scores.get(stockCode)
        if z is None:
            return {
                "stockCode": stockCode,
                "market": market,
                "year": str(year),
                "error": f"{stockCode} 데이터 없음 (universe {total}개 중 미포함, 전년 NI 필요)",
            }
        g = growths.get(stockCode, 0)
        verdict = (
            "positive SUE (PEAD long 후보)"
            if z > 0.5
            else ("negative SUE (drift short 후보)" if z < -0.5 else "neutral")
        )
        return {
            "stockCode": stockCode,
            "market": market,
            "year": str(year),
            "prevYear": str(prev_year_val),
            "score": round(z, 2),
            "growth": round(g, 3),
            "category": verdict,
            "universe": total,
            "interpretation": (
                f"{stockCode} SUE z={round(z, 2)} (YoY NI {g:+.0%}) — {verdict}. Bernard-Thomas 1989 PEAD."
            ),
        }

    return {
        "market": market,
        "year": str(year),
        "prevYear": str(prev_year_val),
        "universe": total,
        "scores": {c: round(s, 2) for c, s in scores.items()},
        "growths": {c: round(g, 3) for c, g in growths.items()},
        "topPos": topPos,
        "topNeg": topNeg,
        "interpretation": (
            f"{market} {year}년 SUE (YoY NI growth z-score, {total}종목) — "
            "positive SUE 상위가 Bernard-Thomas PEAD drift long 후보."
        ),
    }
