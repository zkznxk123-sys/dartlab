"""Frazzini-Pedersen BAB (Betting Against Beta) 횡단면 quant factor.

학술: Frazzini & Pedersen (2014, Journal of Financial Economics) — 저베타 프리미엄.
     BAB = (Low-Beta long leveraged) − (High-Beta short delevereaged)

한계: 실제 beta 추정은 종목별 OLS 필요 (분석 비쌈).

dartlab 단순화 (realized volatility proxy):
    Low-Vol premium ≈ BAB (Baker-Bradley-Wurgler 2011)
    rank(-vol_60d) → 저변동성 분위 = BAB long 후보

일별 close (KRX _hfBulk) 60일 실현변동성, 횡단면 rank.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

log = logging.getLogger(__name__)


def calcBAB(*, market: str = "KR", window: int = 60) -> dict | None:
    """BAB (Betting Against Beta) — 저변동성 프리미엄 횡단면 랭킹.

    Capabilities:
        - 전종목 realized volatility (60일 기본) → 저변동성 rank
        - Top 10 low-vol (BAB long 후보) / Top 10 high-vol (BAB short 후보)
        - Baker-Bradley-Wurgler 저변동성 anomaly

    AIContext:
        - Sprint 2 재무 알파 — 가격 기반 (다른 재무 축과 독립 source)
        - review `babBlock` 시장분석 자동 호출

    Args:
        market: ``"KR"`` 만 지원 (KRX _hfBulk 경유).
        window: realized vol 관측 창 (일). 기본 ``60``.

    Returns:
        dict — market / window / universe / scores / topLow / topHigh / interpretation
    """
    if market != "KR":
        return None

    try:
        from dartlab.gather._hfBulk import loadFiltered
    except ImportError:
        return None

    # 최근 6개월 데이터 (window + buffer)
    try:
        long_df = loadFiltered(adjustment="raw")
    except Exception as exc:  # noqa: BLE001
        log.warning("BAB loadFiltered 실패: %s", type(exc).__name__)
        return None
    if long_df is None or long_df.is_empty():
        return None

    # 일별 close 정렬 후 종목별 log return + vol
    lf = long_df.lazy().select(["BAS_DD", "ISU_CD", "TDD_CLSPRC"]).sort(["ISU_CD", "BAS_DD"], descending=[False, True])
    # 최근 window+1 일만 취함 (효율)
    latest_dates = long_df.get_column("BAS_DD").unique().sort(descending=True).to_list()[: window + 5]
    if len(latest_dates) < window + 1:
        return None
    sub = lf.filter(pl.col("BAS_DD").is_in(latest_dates)).collect()

    scores: dict[str, float] = {}
    for code in sub.get_column("ISU_CD").unique().to_list():
        stock = sub.filter(pl.col("ISU_CD") == code).sort("BAS_DD")
        close = stock.get_column("TDD_CLSPRC").to_numpy().astype(np.float64)
        if len(close) < window:
            continue
        close = close[-window:]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.diff(np.log(close))
        r = r[np.isfinite(r)]
        if len(r) < 30:
            continue
        vol = float(np.std(r, ddof=1) * np.sqrt(252)) * 100
        scores[code] = vol

    if not scores:
        return None

    sorted_items = sorted(scores.items(), key=lambda x: x[1])  # 낮은 순
    topLow = [(c, round(v, 2)) for c, v in sorted_items[:10]]
    topHigh = [(c, round(v, 2)) for c, v in sorted_items[-10:]]

    return {
        "market": market,
        "window": window,
        "universe": len(scores),
        "scores": {c: round(v, 2) for c, v in scores.items()},
        "topLow": topLow,
        "topHigh": topHigh,
        "interpretation": (
            f"{market} BAB ({window}일 realized vol, {len(scores)}종목) — "
            "저변동성 분위가 Frazzini-Pedersen BAB long 후보 (Baker-Bradley-Wurgler 2011 anomaly)."
        ),
    }
