"""Frazzini-Pedersen BAB (Betting Against Beta) 횡단면 quant factor.

학술: Frazzini & Pedersen (2014, Journal of Financial Economics) — 저베타 프리미엄.
     BAB = (Low-Beta long leveraged) − (High-Beta short deleveraged)

dartlab 구현:
    - 기본 점수: 상장시장 벤치마크(KOSPI/KOSDAQ) 대비 252일 OLS beta
    - 보조 점수: 60일 realized volatility (기존 low-vol 프록시 하위호환)
    - 데이터: KRX 종목 HF + KRX 지수 HF (quant.benchmark SSOT)
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import polars as pl

log = logging.getLogger(__name__)


def _dateStart(window: int) -> str:
    return (date.today() - timedelta(days=max(window * 3, 420))).isoformat()


def _benchmarkReturns(indexMarket: str, start: str, *, indexName: str | None = None) -> dict[str, float]:
    """벤치마크 로그수익률 맵: return-date(YYYY-MM-DD) -> log return."""
    from dartlab.quant.benchmark.data import fetchBenchmarkOhlcv

    bench = fetchBenchmarkOhlcv(market=indexMarket, benchmark=indexName, start=start)
    if bench is None or bench.is_empty() or "close" not in bench.columns:
        return {}
    b = bench.sort("date")
    dates = [str(d) for d in b["date"].to_list()]
    close = b["close"].to_numpy().astype(np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        ret = np.diff(np.log(close))
    return {dates[i + 1]: float(ret[i]) for i in range(len(ret)) if np.isfinite(ret[i])}


def _olsBeta(stockDates: list[str], stockRet: np.ndarray, benchRet: dict[str, float]) -> tuple[float | None, int]:
    pairs = [(float(r), benchRet[d]) for d, r in zip(stockDates, stockRet) if d in benchRet and np.isfinite(r)]
    if len(pairs) < 60:
        return None, len(pairs)
    y = np.asarray([p[0] for p in pairs], dtype=np.float64)
    x = np.asarray([p[1] for p in pairs], dtype=np.float64)
    var = float(np.var(x, ddof=1))
    if var <= 0:
        return None, len(pairs)
    cov = float(np.cov(y, x, ddof=1)[0, 1])
    return cov / var, len(pairs)


def calcBAB(
    *,
    market: str = "KR",
    betaWindow: int = 252,
    volWindow: int = 60,
    window: int | None = None,
    stockCode: str | None = None,
    benchmark: str | None = None,
    benchmarkMode: str = "market",
    **kwargs,
) -> dict | None:
    """BAB (Betting Against Beta) — 실제 beta 기반 횡단면 랭킹.

    Capabilities:
        - 전종목 OLS beta (기본 252일) → low-beta / high-beta 후보
        - 60일 realized volatility 보조 랭킹 동시 반환 (기존 low-vol 해석 유지)
        - KOSPI 종목은 코스피, KOSDAQ 종목은 코스닥 지수를 자동 벤치마크로 사용

    Args:
        market: ``"KR"`` 만 지원.
        betaWindow: beta 추정 관측 창. 기본 ``252``.
        volWindow: realized vol 관측 창. 기본 ``60``.
        window: 하위호환 별칭. 전달 시 ``volWindow`` 로 사용.
        stockCode: 단일 종목 조회 시 해당 종목의 beta/vol percentile 반환.
        benchmark: 명시 벤치마크. 지정하면 모든 종목에 같은 지수를 사용.
        benchmarkMode: ``"market"`` | ``"sector"`` | ``"style"``. 기본 ``"market"``.

    Returns:
        dict — market / betaWindow / volWindow / universe / scores / topLow / topHigh
        / volScores / topLowVol / topHighVol / interpretation.

    Guide:
        Frazzini-Pedersen 2014 BAB. KR 만 지원. 252 봉 일별 OLS β + 60 봉 vol 보조 랭킹.

    When:
        Cross-sectional BAB strategy + AI low-beta 종목 답변.

    How:
        전종목 OLS β → percentile 랭킹 → topLow/High 추출. 종목별 sector 벤치 자동.

    Requires:
        KR 종목 + 252+ 봉 가격 데이터.

    Raises:
        없음 — KR 외 또는 데이터 부족 시 None.

    Example:
        >>> r = calcBAB(market="KR", stockCode="005930")
        >>> r["stockResult"]["betaPercentile"]
        0.32

    SeeAlso:
        - factor.calc.decomposeFactor : 단일 종목 β
        - portfolio.optimize.allocateERC : low-vol weighting

    AIContext:
        "BAB low-beta 종목 추천" 답변 시 topLow + interpretation 인용.
    """
    if market != "KR":
        return None
    if window is not None:
        volWindow = int(window)

    try:
        from dartlab.gather.bulkData.hfBulk import loadFiltered
        from dartlab.quant.benchmark.data import resolveBenchmark
    except ImportError:
        return None

    start = kwargs.get("start") or _dateStart(max(betaWindow, volWindow))
    try:
        long_df = loadFiltered(start=start, adjustment="raw")
    except Exception as exc:  # noqa: BLE001
        log.warning("BAB loadFiltered 실패: %s", type(exc).__name__)
        return None
    if long_df is None or long_df.is_empty():
        return None

    latest_dates = (
        long_df.get_column("BAS_DD").unique().sort(descending=True).to_list()[: max(betaWindow, volWindow) + 5]
    )
    if len(latest_dates) < min(60, betaWindow):
        return None
    sub = (
        long_df.filter(pl.col("BAS_DD").is_in(latest_dates))
        .select(["BAS_DD", "ISU_CD", "MKT_NM", "TDD_CLSPRC"])
        .sort(["ISU_CD", "BAS_DD"])
    )

    bench_maps = {
        ("KOSPI", "코스피"): _benchmarkReturns("KOSPI", start),
        ("KOSDAQ", "코스닥"): _benchmarkReturns("KOSDAQ", start),
    }
    if benchmark:
        bm = resolveBenchmark(None, market="KR", benchmark=benchmark)
        bench_maps[(bm["indexMarket"], bm["indexName"])] = _benchmarkReturns(
            bm["indexMarket"],
            start,
            indexName=bm["indexName"],
        )

    beta_scores: dict[str, float] = {}
    vol_scores: dict[str, float] = {}
    obs: dict[str, int] = {}
    benchmark_used: dict[str, dict] = {}

    for part in sub.partition_by("ISU_CD", as_dict=False):
        if part.height < min(61, max(betaWindow, volWindow)):
            continue
        code = part["ISU_CD"][0]
        close = part["TDD_CLSPRC"].to_numpy().astype(np.float64)
        dates = part["BAS_DD"].to_list()
        with np.errstate(divide="ignore", invalid="ignore"):
            ret = np.diff(np.log(close))
        ret_dates = [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in dates[1:]]

        r_beta = ret[-betaWindow:] if len(ret) >= betaWindow else ret
        d_beta = ret_dates[-len(r_beta) :]
        if benchmark:
            bm_meta = resolveBenchmark(code, market="KR", benchmark=benchmark)
        elif benchmarkMode == "market":
            bm_meta = resolveBenchmark(code, market="KR")
        else:
            bm_meta = resolveBenchmark(code, market="KR", benchmarkMode=benchmarkMode)
        bm_key = (bm_meta["indexMarket"], bm_meta["indexName"])
        if bm_key not in bench_maps:
            bench_maps[bm_key] = _benchmarkReturns(bm_key[0], start, indexName=bm_key[1])
        benchRet = bench_maps.get(bm_key, {})
        beta, nObs = _olsBeta(d_beta, r_beta, benchRet or {})
        if beta is not None and np.isfinite(beta):
            beta_scores[code] = float(beta)
            obs[code] = int(nObs)
            benchmark_used[code] = bm_meta

        if len(ret) >= min(30, volWindow):
            r_vol = ret[-volWindow:]
            r_vol = r_vol[np.isfinite(r_vol)]
            if len(r_vol) >= 30:
                vol_scores[code] = float(np.std(r_vol, ddof=1) * np.sqrt(252)) * 100

    if not beta_scores:
        return None

    beta_items = sorted(beta_scores.items(), key=lambda x: x[1])
    vol_items = sorted(vol_scores.items(), key=lambda x: x[1])
    total = len(beta_scores)

    if stockCode:
        b = beta_scores.get(stockCode)
        v = vol_scores.get(stockCode)
        if b is None:
            return {
                "stockCode": stockCode,
                "market": market,
                "error": f"{stockCode} beta 데이터 없음 (universe {total}개 중 미포함)",
            }
        rank_low = sum(1 for x in beta_scores.values() if x <= b)
        pct_low = round(100 * rank_low / total, 1)
        vol_pct = None
        if v is not None and vol_scores:
            vol_pct = round(100 * sum(1 for x in vol_scores.values() if x <= v) / len(vol_scores), 1)
        category = "low-beta (BAB long 후보)" if pct_low <= 30 else ("mid-beta" if pct_low <= 70 else "high-beta")
        return {
            "stockCode": stockCode,
            "market": market,
            "betaWindow": betaWindow,
            "volWindow": volWindow,
            "score": round(b, 4),
            "beta": round(b, 4),
            "betaPercentile": pct_low,
            "vol": round(v, 2) if v is not None else None,
            "volPercentile": vol_pct,
            "category": category,
            "nObs": obs.get(stockCode),
            "benchmarkUsed": benchmark_used.get(stockCode),
            "benchmarkMode": benchmarkMode,
            "universe": total,
            "interpretation": (
                f"{stockCode} beta={round(b, 3)} ({betaWindow}일, 저베타 백분위 {pct_low}) — {category}. "
                f"60일 realized vol={round(v, 2) if v is not None else 'N/A'}%."
            ),
        }

    topLow = [(c, round(v, 4)) for c, v in beta_items[:10]]
    topHigh = [(c, round(v, 4)) for c, v in beta_items[-10:]]
    topLowVol = [(c, round(v, 2)) for c, v in vol_items[:10]]
    topHighVol = [(c, round(v, 2)) for c, v in vol_items[-10:]]

    return {
        "market": market,
        "betaWindow": betaWindow,
        "volWindow": volWindow,
        "window": volWindow,
        "universe": total,
        "scores": {c: round(v, 4) for c, v in beta_scores.items()},
        "volScores": {c: round(v, 2) for c, v in vol_scores.items()},
        "topLow": topLow,
        "topHigh": topHigh,
        "topLowVol": topLowVol,
        "topHighVol": topHighVol,
        "method": "OLS beta vs KRX index; realized vol retained as secondary signal",
        "benchmarkMode": benchmarkMode,
        "interpretation": (
            f"{market} BAB ({betaWindow}일 beta, {total}종목) — "
            "저베타 분위가 Frazzini-Pedersen BAB long 후보. "
            f"{volWindow}일 realized vol은 보조 저변동성 신호로 함께 제공."
        ),
    }
