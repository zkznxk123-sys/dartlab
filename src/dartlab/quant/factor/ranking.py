"""멀티팩터 복합 순위 (횡단면).

학술 근거: Asness et al. (2013) — Value and Momentum Everywhere.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.quant.screen.dataAccess import loadScanParquet
from dartlab.quant.strategy.metrics import pearsonCorr, spearmanCorr
from dartlab.synth.scanBridge import (
    extractAnnualConsolidated,
    getAccountValue,
    isEdgarSchema,
)

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Grinold Ch.5-6 — 횡단면 IC
# ══════════════════════════════════════════════════════════════════════
#
# IC_t = corr(factorScore_{i,t}, forwardReturn_{i, t→t+h})  for all i
#
# 단일 종목 시계열 IR (factor.py) 과 구분. 이 모듈은 **한 시점에서 전종목 팩터
# 스코어가 종목을 잘 정렬하는가** 의 Grinold 정의 IC.


def calcCrossSectionIC(
    factorScores: dict[str, float],
    forwardReturns: dict[str, float],
) -> dict:
    """한 시점의 횡단면 IC (Pearson + Spearman + t-stat).

    Returns dict with ic_pearson, ic_spearman, n_stocks, t_stat, is_significant.
    """
    common = sorted(set(factorScores) & set(forwardReturns))
    if len(common) < 10:
        return {
            "ic_pearson": float("nan"),
            "ic_spearman": float("nan"),
            "n_stocks": len(common),
            "t_stat": None,
            "is_significant": False,
        }
    x = np.array([factorScores[k] for k in common], dtype=float)
    y = np.array([forwardReturns[k] for k in common], dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if x.size < 10:
        return {
            "ic_pearson": float("nan"),
            "ic_spearman": float("nan"),
            "n_stocks": int(x.size),
            "t_stat": None,
            "is_significant": False,
        }
    ic_p = pearsonCorr(x, y)
    ic_s = spearmanCorr(x, y)
    n = int(x.size)
    t_stat: float | None = None
    perfect = not np.isnan(ic_p) and abs(ic_p) >= 0.9999
    if not np.isnan(ic_p) and not perfect and n > 2:
        denom = np.sqrt(max(1.0 - ic_p * ic_p, 1e-12))
        t_stat = float(ic_p * np.sqrt(n - 2) / denom)
    return {
        "ic_pearson": float(ic_p),
        "ic_spearman": float(ic_s),
        "n_stocks": n,
        "t_stat": t_stat,
        "is_significant": perfect or (t_stat is not None and abs(t_stat) > 2.0),
    }


def icTimeSeries(
    factorScoresSeries: list[dict[str, float]],
    forwardReturnsSeries: list[dict[str, float]],
) -> dict:
    """IC 시계열 통계 — 여러 시점 IC 의 평균/표준편차/ICIR.

    Parameters
    ----------
    factorScoresSeries : list[dict[str, float]]
        시점별 {종목코드: 팩터 스코어} dict 리스트.
    forwardReturnsSeries : list[dict[str, float]]
        시점별 {종목코드: forward return} dict 리스트 (동일 길이).

    Returns
    -------
    dict
        mean_ic : float — 평균 Spearman IC (비율)
        std_ic : float — IC 표준편차 (비율)
        icir : float — ICIR = mean_ic / std_ic (배)
        n_periods : int — 유효 기간 수
        hit_rate : float — IC 부호 일치 비율 (0~1)
    """
    if len(factorScoresSeries) != len(forwardReturnsSeries):
        raise ValueError("factorScoresSeries / forwardReturnsSeries 길이 불일치")
    ics: list[float] = []
    for fs, fr in zip(factorScoresSeries, forwardReturnsSeries):
        r = calcCrossSectionIC(fs, fr)
        ic = r.get("ic_spearman")
        if ic is not None and not (isinstance(ic, float) and np.isnan(ic)):
            ics.append(float(ic))
    if len(ics) < 2:
        return {
            "mean_ic": float("nan"),
            "std_ic": float("nan"),
            "icir": float("nan"),
            "n_periods": len(ics),
            "hit_rate": float("nan"),
        }
    arr = np.array(ics, dtype=float)
    mean_ic = float(arr.mean())
    std_ic = float(arr.std(ddof=1))
    icir = float(mean_ic / std_ic) if std_ic > 0 else 0.0
    hit_rate = float(np.mean(np.sign(arr) == np.sign(mean_ic)))
    return {
        "mean_ic": mean_ic,
        "std_ic": std_ic,
        "icir": icir,
        "n_periods": len(ics),
        "hit_rate": hit_rate,
    }


def _parse(val) -> float | None:
    """문자열/숫자 → float. core SSOT 사용."""
    if isinstance(val, (int, float)):
        return float(val)
    from dartlab.core.utils.helpers import parseNumStr

    return parseNumStr(val)


def _loadAccount(lf: pl.LazyFrame, sj: str, account: str, year: str) -> dict[str, float]:
    """특정 계정의 전종목 금액 추출 — scanBridge 경유 DART/EDGAR 통일."""
    try:
        full = lf.collect(engine="streaming")
    except (KeyError, ValueError, TypeError, AttributeError):
        return {}
    annual = extractAnnualConsolidated(full)
    if annual.is_empty():
        return {}
    return getAccountValue(annual, account, year=year)


def calcRanking(*, market: str = "KR", stockCode: str | None = None, **kwargs) -> dict:
    """전종목 5-팩터 멀티팩터 복합 순위 (Phase B3 정정).

    2026-04-24: size (marketCap) + value (bookYield) 팩터 추가 → 5팩터 (margin/ROA/debt/size/value).
    KR: KRX 시총 직접 사용. US: size/value 미사용 (시총 미수집) — 기존 3팩터.

    학술 근거:
    - Asness et al. (2013): Value and Momentum Everywhere
    - Fama & French (1992): size + BM 팩터
    - Piotroski (2000): Fundamentals score (ROA, margin, debt)

    Parameters
    ----------
    market : str
        시장. 기본 "KR".
    stockCode : str | None
        특정 종목 지정 시 해당 종목 순위 + 상위 10 반환.

    Returns
    -------
    dict
        market : str — 시장
        year : str — 기준 연도
        totalStocks : int — 순위 산출 종목 수
        factorsUsed : list[str] — 사용된 팩터 리스트
        rankings : list[dict] — 상위 종목 리스트 (최대 50개)
            stockCode : str — 6자리 종목코드
            opMargin : float — 영업이익률 (%)
            ROA : float — 총자산수익률 (%)
            debtRatio : float — 부채비율 (%)
            marketCap : float — 시가총액 (원, KR 만)
            bookYield : float — equity/marketCap (= 1/PBR, KR 만)
            compositeScore : float — 복합 백분위 (0~1, 1=top)
            rank : int — 순위
        target : dict | None — stockCode 지정 시 해당 종목 정보
    """
    result: dict = {"market": market}

    lf = loadScanParquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}

    # 최신 연도 확인
    edgar = isEdgarSchema(lf)
    yearCol = "fy" if edgar else "bsns_year"
    try:
        years = lf.select(yearCol).unique().collect(engine="streaming").to_series().sort(descending=True).to_list()
        years = [str(y) for y in years]
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        return {**result, "error": str(e)}

    if not years:
        return {**result, "error": "연도 데이터 없음"}

    # 데이터가 풍부한 연도 선택 (최신 → fallback)
    year = None
    for y in years:
        assets_test = _loadAccount(lf, "BS", "자산총계", y)
        if len(assets_test) >= 100:
            year = y
            break
    if year is None:
        year = years[0]
    result["year"] = year

    # 계정별 전종목 추출 (LazyFrame 필터로 메모리 안전)
    sales = _loadAccount(lf, "IS", "매출액", year)
    op = _loadAccount(lf, "IS", "영업이익", year)
    ni = _loadAccount(lf, "IS", "당기순이익", year)
    assets = _loadAccount(lf, "BS", "자산총계", year)
    debt = _loadAccount(lf, "BS", "부채총계", year)
    equity = _loadAccount(lf, "BS", "자본총계", year)

    # 시총 (KR 만) — size + bookYield 팩터용
    market_caps: dict[str, float] = {}
    if market == "KR":
        try:
            from dartlab.gather.bulkData.hfBulk import loadFiltered

            mc_long = loadFiltered(start=f"{year}-12-25", end=f"{year}-12-31", adjustment="raw")
            if mc_long is not None and not mc_long.is_empty():
                latest = (
                    mc_long.sort("BAS_DD", descending=True)
                    .unique(subset=["ISU_CD"], keep="first")
                    .select(["ISU_CD", "MKTCAP"])
                )
                market_caps = {
                    row["ISU_CD"]: float(row["MKTCAP"])
                    for row in latest.iter_rows(named=True)
                    if row.get("MKTCAP") and row["MKTCAP"] > 0
                }
        except Exception as exc:
            log.warning("ranking: KR 시총 fetch 실패: %s", type(exc).__name__)

    # 공통 종목
    all_codes = set(sales) & set(assets)
    if not all_codes:
        return {**result, "error": "공통 종목 없음"}

    # 지표 계산
    has_size_value = market == "KR" and len(market_caps) >= 100
    ranked = []
    for code in all_codes:
        s = sales.get(code, 0)
        o = op.get(code)
        n = ni.get(code)
        a = assets.get(code, 0)
        d = debt.get(code, 0)
        eq = equity.get(code)

        margin = (o / s * 100) if s > 0 and o is not None else None
        roa = (n / a * 100) if a > 0 and n is not None else None
        dr = (d / a * 100) if a > 0 else None
        mc = market_caps.get(code) if has_size_value else None
        by = (eq / mc) if (has_size_value and mc and mc > 0 and eq is not None and eq > 0) else None

        if margin is not None or roa is not None:
            ranked.append(
                {
                    "stockCode": code,
                    "opMargin": round(margin, 2) if margin else None,
                    "ROA": round(roa, 2) if roa else None,
                    "debtRatio": round(dr, 2) if dr else None,
                    "marketCap": round(mc, 0) if mc else None,
                    "bookYield": round(by, 4) if by else None,
                }
            )

    if not ranked:
        return {**result, "error": "순위 산출 가능 종목 없음"}

    # 백분위 순위
    n = len(ranked)
    margins = np.array([r["opMargin"] or 0 for r in ranked])
    roas = np.array([r["ROA"] or 0 for r in ranked])
    debts = np.array([r["debtRatio"] or 100 for r in ranked])

    m_rank = np.argsort(np.argsort(-margins)) / max(n - 1, 1)
    r_rank = np.argsort(np.argsort(-roas)) / max(n - 1, 1)
    d_rank = np.argsort(np.argsort(debts)) / max(n - 1, 1)

    # 5-factor composite (KR 시총 있을 때) 또는 3-factor (fallback)
    if has_size_value:
        # size: 작을수록 top (small premium) — 근데 한국 2025 RMW 검증으로 size 역방향
        # 실용: 큰 시총 = 안정성 ↑ 가 더 적절. size_rank = 큰 시총 top (역발상 제거)
        mcaps = np.array([r["marketCap"] or 0 for r in ranked])
        yields_ = np.array([r["bookYield"] or 0 for r in ranked])
        # size_rank: 시총 큰 종목이 top (실용적 안정성)
        s_rank = np.argsort(np.argsort(-mcaps)) / max(n - 1, 1)
        # value_rank: bookYield 큰 종목 top (= 낮은 PBR = value)
        v_rank = np.argsort(np.argsort(-yields_)) / max(n - 1, 1)
        composites = (m_rank + r_rank + d_rank + s_rank + v_rank) / 5
        factors_used = ["margin", "ROA", "debt", "size", "value"]
    else:
        composites = (m_rank + r_rank + d_rank) / 3
        factors_used = ["margin", "ROA", "debt"]
    order = np.argsort(-composites)

    for i, idx in enumerate(order):
        ranked[idx]["compositeScore"] = round(float(composites[idx]), 4)
        ranked[idx]["rank"] = i + 1

    sorted_ranked = sorted(ranked, key=lambda x: x.get("rank", 9999))
    result["totalStocks"] = n
    result["factorsUsed"] = factors_used

    if stockCode:
        target = [r for r in sorted_ranked if r["stockCode"] == stockCode]
        result["target"] = target[0] if target else None
        result["rankings"] = sorted_ranked[:10]
    else:
        result["rankings"] = sorted_ranked[:50]

    return result
