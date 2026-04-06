"""팩터 분해 — book-based 횡단면 SMB/HML/RMW/CMA로 회귀.

학술 근거:
- Fama & French (2015): 5-factor model (MKT, SMB, HML, RMW, CMA)
- Hou, Xue, Zhang (2015): q-factor model (별도 구현 예정, 현재는 FF5만)

데이터 흐름:
1. factorBuild.build_factors(market) — scan finance.parquet에서 5분위 포트폴리오
   구성, 동일가중 평균 일별 log return → SMB/HML/RMW/CMA 시계열
2. analyze_factor — 단일 종목 vs (MKT + 빌드된 팩터) 다변수 OLS

이전 버전(2026-04-06 이전)은 변동성 합성 가짜 프록시를 사용했고 audit에서 진짜
SMB와 음의 상관(−0.51)이 발견됨. 이번 재구현으로 폐기. 자세한 내용은
data/dart/auditQuant/factor.md 참조.

⚠️ 한계:
- size proxy = book equity (시가총액 데이터 미수집). 시총 인프라 추가 후 진짜 시총으로 교체.
- BM proxy = equity/assets. 시총 부재로 진짜 BM 불가.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from dartlab.quant._helpers import fetch_benchmark, fetch_ohlcv, ohlcv_to_arrays, resolve_market

log = logging.getLogger(__name__)


def analyze_factor(stockCode: str, *, market: str = "auto", **kwargs: Any) -> dict:
    """진짜 횡단면 팩터 시계열로 단일 종목 회귀.

    Args:
        stockCode: 종목코드 또는 ticker.
        market: "KR" | "US" | "auto".

    Returns:
        dict — MKT/SMB/HML/RMW/CMA 로딩 + alpha + R² + 데이터 적정성 + 한계 명시.
    """
    market = resolve_market(stockCode, market)

    ohlcv = fetch_ohlcv(stockCode, **kwargs)
    if ohlcv is None or ohlcv.is_empty():
        return {"error": f"{stockCode} 주가 데이터 없음"}
    arr = ohlcv_to_arrays(ohlcv)
    close = arr.get("close")
    if close is None or len(close) < 60:
        return {"error": f"{stockCode} 데이터 부족 (최소 60일)"}
    stock_ret = np.diff(np.log(close))

    bench = fetch_benchmark(market)
    if bench is None or bench.is_empty():
        return {"error": "벤치마크 데이터 없음"}
    bench_close = ohlcv_to_arrays(bench).get("close")
    if bench_close is None:
        return {"error": "벤치마크 close 없음"}
    bench_ret = np.diff(np.log(bench_close))

    # 진짜 횡단면 팩터 시계열 빌드/로드
    if market == "KR":
        from dartlab.quant.factorBuild import build_factors

        factors = build_factors(market)
    else:
        factors = None  # US는 후순위

    if factors is None:
        # fallback: 1-factor CAPM (MKT만)
        return _capm_fallback(stockCode, market, stock_ret, bench_ret)

    smb = factors["smb"]
    hml = factors["hml"]
    rmw = factors.get("rmw")
    cma = factors.get("cma")

    # 길이 정렬
    ml = min(len(stock_ret), len(bench_ret), len(smb), len(hml))
    if rmw is not None:
        ml = min(ml, len(rmw))
    if cma is not None:
        ml = min(ml, len(cma))
    if ml < 30:
        return {"error": f"공통 기간 부족 ({ml}일)"}

    y = stock_ret[-ml:]
    cols = [bench_ret[-ml:], smb[-ml:], hml[-ml:]]
    names = ["MKT", "SMB", "HML"]
    if rmw is not None:
        cols.append(rmw[-ml:])
        names.append("RMW")
    if cma is not None:
        cols.append(cma[-ml:])
        names.append("CMA")

    X = np.column_stack(cols)
    betas, alpha_val, r2, t_stats = _multi_ols(y, X)

    result: dict = {
        "stockCode": stockCode,
        "market": market,
        "model": f"FF{len(names)}-real" if rmw is not None and cma is not None else f"FF{len(names)}",
        "dataPoints": int(ml),
        "dataAdequacy": "low" if ml < 252 else "ok",
        "alpha": round(float(alpha_val * 252), 4),
        "rSquared": round(float(r2), 4),
        "factorYear": factors["year"],
        "factorUniverse": factors["universe"],
        "factorNotes": factors.get("notes"),
    }

    for i, name in enumerate(names):
        result[name] = {
            "loading": round(float(betas[i]), 4),
            "tstat": round(float(t_stats[i]), 2) if t_stats is not None else None,
        }

    # 팩터 기여도 (연환산)
    contributions = {}
    for i, name in enumerate(names):
        contributions[name] = round(float(betas[i] * np.mean(X[:, i]) * 252), 4)
    result["contributions"] = contributions

    result["interpretation"] = _interpret(result, names)

    return result


def factor_exposure_limits(loadings: dict, *, limits: dict | None = None) -> dict:
    """팩터 익스포저 한도 체크 (책 7장 — 팩터 리스크 관리).

    Args:
        loadings: {factor_name: loading_value} (analyze_factor 결과의 항목)
        limits: {factor_name: max_abs}. None이면 기본값 사용.

    Returns:
        dict — 각 팩터의 |loading|, 한도 초과 여부, 권장 헤지비율.
    """
    if limits is None:
        # 기본: MKT 1.5, 나머지 0.5 (보수적)
        limits = {"MKT": 1.5, "SMB": 0.5, "HML": 0.5, "RMW": 0.5, "CMA": 0.5}

    breaches = []
    for name, lim in limits.items():
        info = loadings.get(name)
        if not isinstance(info, dict):
            continue
        ld = float(info.get("loading", 0))
        if abs(ld) > lim:
            # 헤지: 초과분만큼 반대 방향
            hedge_size = -(ld - np.sign(ld) * lim)
            breaches.append(
                {
                    "factor": name,
                    "loading": ld,
                    "limit": lim,
                    "excess": round(ld - np.sign(ld) * lim, 4),
                    "hedgeSize": round(float(hedge_size), 4),
                }
            )

    return {"limits": limits, "breaches": breaches, "compliant": len(breaches) == 0}


def hedge_ratio(target_loading: float, hedge_loading: float) -> float:
    """단일 팩터 헤지비율 — target / hedge.

    예: 포트의 SMB loading +0.8을 헤지하려면 SMB-vehicle의 SMB loading이
    +1.0인 경우 hedge_ratio = -0.8 (포트 1당 hedge -0.8).
    """
    if hedge_loading == 0:
        return 0.0
    return float(-target_loading / hedge_loading)


def _capm_fallback(stockCode: str, market: str, sr: np.ndarray, br: np.ndarray) -> dict:
    """팩터 빌드 실패 시 1-factor CAPM."""
    ml = min(len(sr), len(br))
    if ml < 30:
        return {"error": "공통 기간 부족"}
    y = sr[-ml:]
    x = br[-ml:]
    cov = float(np.cov(y, x, ddof=1)[0, 1])
    var = float(np.var(x, ddof=1))
    beta = cov / var if var > 0 else 0
    alpha = float(np.mean(y) - beta * np.mean(x))
    yhat = alpha + beta * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    return {
        "stockCode": stockCode,
        "market": market,
        "model": "CAPM-fallback",
        "info": "factorBuild 실패 → 1-factor CAPM으로 fallback",
        "dataPoints": int(ml),
        "MKT": {"loading": round(beta, 4), "tstat": None},
        "alpha": round(alpha * 252, 4),
        "rSquared": round(r2, 4),
    }


def _multi_ols(y, X):
    """다변수 OLS + t-stats."""
    n, k = X.shape
    X_aug = np.column_stack([np.ones(n), X])
    try:
        beta = np.linalg.lstsq(X_aug, y, rcond=None)[0]
        y_hat = X_aug @ beta
        resid = y - y_hat
        ss_res = float(np.sum(resid**2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        t_stats = None
        if n > k + 1:
            mse = ss_res / (n - k - 1)
            try:
                cov = mse * np.linalg.inv(X_aug.T @ X_aug)
                se = np.sqrt(np.diag(cov))
                t_stats = beta / se
                t_stats = t_stats[1:]
            except np.linalg.LinAlgError:
                pass

        return beta[1:], float(beta[0]), r2, t_stats
    except np.linalg.LinAlgError:
        return np.zeros(k), 0.0, 0.0, None


def _interpret(result: dict, names: list[str]) -> list[str]:
    interp = []
    for name in names:
        info = result.get(name)
        if not isinstance(info, dict):
            continue
        ld = info.get("loading", 0)
        ts = info.get("tstat")
        sig = ts is not None and abs(ts) > 2.0

        if name == "MKT":
            if ld > 1.2:
                interp.append(f"공격적 시장 민감도 (β={ld:.2f})")
            elif ld < 0.8:
                interp.append(f"방어적 (β={ld:.2f})")
        elif sig:
            labels = {
                "SMB": ("소형주 특성", "대형주 특성"),
                "HML": ("고BM(가치)", "저BM(성장)"),
                "RMW": ("고수익성(profitable)", "저수익성(weak)"),
                "CMA": ("보수적 투자(conservative)", "공격적 투자(aggressive)"),
            }
            pos, neg = labels.get(name, ("양", "음"))
            interp.append(pos if ld > 0 else neg)

    return interp
