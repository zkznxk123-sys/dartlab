"""멀티팩터 복합 순위 (횡단면).

학술 근거: Asness et al. (2013) — Value and Momentum Everywhere.
"""

from __future__ import annotations

import logging

import numpy as np
import polars as pl

from dartlab.quant._helpers import load_scan_parquet
from dartlab.quant.strategy.metrics import pearsonCorr, spearmanCorr

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
    """IC 시계열 통계 — 여러 시점 IC 의 평균/표준편차/ICIR."""
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
    from dartlab.core.finance.helpers import parseNumStr

    return parseNumStr(val)


def _load_account(lf: pl.LazyFrame, sj: str, account: str, year: str) -> dict[str, float]:
    """특정 계정의 전종목 금액 추출. LazyFrame 필터 → collect."""
    # 연결 + 해당 연도 + 계정
    try:
        df = (
            lf.filter(pl.col("bsns_year") == year)
            .filter(pl.col("fs_nm").str.contains("연결"))
            .filter(pl.col("sj_div") == sj)
            .filter(pl.col("account_nm") == account)
            .select("stockCode", "thstrm_amount")
            .collect()
        )
    except Exception:  # noqa: BLE001
        df = None

    # fallback: 연결 없으면 전체
    if df is None or df.is_empty():
        try:
            df = (
                lf.filter(pl.col("bsns_year") == year)
                .filter(pl.col("sj_div") == sj)
                .filter(pl.col("account_nm") == account)
                .select("stockCode", "thstrm_amount")
                .collect()
            )
        except Exception:  # noqa: BLE001
            return {}

    if df is None or df.is_empty():
        return {}

    result = {}
    for row in df.iter_rows(named=True):
        code = row.get("stockCode")
        val = _parse(row.get("thstrm_amount"))
        if code and val is not None and code not in result:
            result[code] = val
    return result


def calcRanking(*, market: str = "KR", stockCode: str | None = None, **kwargs) -> dict:
    """전종목 멀티팩터 복합 순위."""
    result: dict = {"market": market}

    lf = load_scan_parquet("finance", market)
    if lf is None:
        return {**result, "error": "finance.parquet 없음"}

    # 최신 연도 확인
    try:
        years = lf.select("bsns_year").unique().collect().to_series().sort(descending=True).to_list()
    except Exception as e:  # noqa: BLE001
        return {**result, "error": str(e)}

    if not years:
        return {**result, "error": "연도 데이터 없음"}

    # 데이터가 풍부한 연도 선택 (최신 → fallback)
    year = None
    for y in years:
        assets_test = _load_account(lf, "BS", "자산총계", y)
        if len(assets_test) >= 100:
            year = y
            break
    if year is None:
        year = years[0]
    result["year"] = year

    # 계정별 전종목 추출 (LazyFrame 필터로 메모리 안전)
    sales = _load_account(lf, "IS", "매출액", year)
    op = _load_account(lf, "IS", "영업이익", year)
    ni = _load_account(lf, "IS", "당기순이익", year)
    assets = _load_account(lf, "BS", "자산총계", year)
    debt = _load_account(lf, "BS", "부채총계", year)

    # 공통 종목
    all_codes = set(sales) & set(assets)
    if not all_codes:
        return {**result, "error": "공통 종목 없음"}

    # 지표 계산
    ranked = []
    for code in all_codes:
        s = sales.get(code, 0)
        o = op.get(code)
        n = ni.get(code)
        a = assets.get(code, 0)
        d = debt.get(code, 0)

        margin = (o / s * 100) if s > 0 and o is not None else None
        roa = (n / a * 100) if a > 0 and n is not None else None
        dr = (d / a * 100) if a > 0 else None

        if margin is not None or roa is not None:
            ranked.append(
                {
                    "stockCode": code,
                    "opMargin": round(margin, 2) if margin else None,
                    "ROA": round(roa, 2) if roa else None,
                    "debtRatio": round(dr, 2) if dr else None,
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
    composites = (m_rank + r_rank + d_rank) / 3
    order = np.argsort(-composites)

    for i, idx in enumerate(order):
        ranked[idx]["compositeScore"] = round(float(composites[idx]), 4)
        ranked[idx]["rank"] = i + 1

    sorted_ranked = sorted(ranked, key=lambda x: x.get("rank", 9999))
    result["totalStocks"] = n

    if stockCode:
        target = [r for r in sorted_ranked if r["stockCode"] == stockCode]
        result["target"] = target[0] if target else None
        result["rankings"] = sorted_ranked[:10]
    else:
        result["rankings"] = sorted_ranked[:50]

    return result
