"""Bottom-up Beta — Damodaran Hamada Unlever/Relever.

Damodaran *Investment Valuation* Ch.7:
    β_U = β_L / (1 + (1 - t) × D/E)    # Hamada unlever
    β_L(firm) = β_U(peer mean) × (1 + (1 - t) × D/E(firm))  # relever

섹터 peer 평균 unlevered β 가 개별 기업 β 보다 안정적 (noise 제거).
scipy 무의존 — 평균/중앙값/난수만 사용.
"""

from __future__ import annotations

import random
from statistics import mean, median
from typing import Any


def calcBottomUpBeta(
    *,
    sector: str,
    debtToEquity: float,
    taxRate: float = 0.22,
    peerLimit: int = 20,
    country: str = "KR",
) -> dict[str, Any]:
    """Hamada unlever/relever — 섹터 peer 평균 unlevered β → 자기 D/E 로 relever.

    Parameters
    ----------
    sector : 섹터/산업그룹명 (industryGroup 권장).
    debtToEquity : 자기 D/E (시장가 기준 권장, 없으면 book).
    taxRate : 유효세율 (0.0~0.5).
    peerLimit : peer 샘플 최대 수.
    country : ISO2 (peer 필터링은 현재 KR 만 지원, 다른 국가 fallback).

    Returns
    -------
    dict
        leveredBeta : float — relevered β (자기 D/E 적용)
        unleveredBetaMean : float — peer unlevered 평균
        unleveredBetaMedian : float
        peerCount : int
        method : "bottom_up" | "sector_default" | "fallback_one"
        peers : list[{code, betaLevered, de, betaUnlevered}]
        sector : str
        debtToEquity : float
    """
    tax = max(0.0, min(0.5, float(taxRate)))
    de = max(0.0, float(debtToEquity))

    # peer 추출 (KR + scan/finance.parquet)
    peers: list[dict[str, Any]] = []
    if country == "KR":
        peers = _extractKrPeers(sector, peerLimit)

    if len(peers) < 5:
        # sector_default fallback
        from dartlab.core.sector import getSectorParamsByName

        sector_beta: float | None = None
        try:
            sp = getSectorParamsByName(sector)
            if sp and hasattr(sp, "beta") and sp.beta:
                sector_beta = float(sp.beta)
        except (AttributeError, ValueError, TypeError):
            pass

        if sector_beta is not None:
            return {
                "leveredBeta": round(sector_beta, 3),
                "unleveredBetaMean": None,
                "unleveredBetaMedian": None,
                "peerCount": len(peers),
                "method": "sector_default",
                "peers": peers,
                "sector": sector,
                "debtToEquity": de,
            }

        return {
            "leveredBeta": 1.0,
            "unleveredBetaMean": None,
            "unleveredBetaMedian": None,
            "peerCount": len(peers),
            "method": "fallback_one",
            "peers": peers,
            "sector": sector,
            "debtToEquity": de,
        }

    # 각 peer unlever
    unlevered: list[float] = []
    for p in peers:
        beta_l = p.get("betaLevered")
        p_de = p.get("de", 0.3)
        if beta_l is None or beta_l <= 0:
            continue
        try:
            beta_u = beta_l / (1.0 + (1.0 - tax) * p_de)
        except ZeroDivisionError:
            continue
        if 0.1 < beta_u < 3.0:  # sanity
            unlevered.append(beta_u)
            p["betaUnlevered"] = round(beta_u, 3)

    if len(unlevered) < 5:
        return {
            "leveredBeta": 1.0,
            "unleveredBetaMean": None,
            "unleveredBetaMedian": None,
            "peerCount": len(unlevered),
            "method": "fallback_one",
            "peers": peers,
            "sector": sector,
            "debtToEquity": de,
        }

    mu = mean(unlevered)
    med = median(unlevered)

    # Relever (자기 D/E)
    levered = mu * (1.0 + (1.0 - tax) * de)
    levered = max(0.3, min(levered, 3.0))  # sanity

    return {
        "leveredBeta": round(levered, 3),
        "unleveredBetaMean": round(mu, 3),
        "unleveredBetaMedian": round(med, 3),
        "peerCount": len(unlevered),
        "method": "bottom_up",
        "peers": peers[:peerLimit],
        "sector": sector,
        "debtToEquity": de,
    }


def _extractKrPeers(sector: str, limit: int) -> list[dict[str, Any]]:
    """scan/finance.parquet → 동일 섹터 peer 의 β + D/E 추출.

    현재 sectorParams.json 에 개별 종목 매핑이 없으므로 단순화:
    - 섹터별 대표 β 를 peer 각자에 동일 적용 (지금은 peer D/E 만 계산)
    - 더 정교한 구현은 beta 수익률 회귀 (향후 개선)

    반환: peer list [{code, betaLevered, de, betaUnlevered}]
    """
    try:
        import importlib

        import polars as pl

        _scanHelpers = importlib.import_module("dartlab.scan._helpers")
        _ensureScanData = _scanHelpers._ensureScanData
        parseNumStr = _scanHelpers.parseNumStr
    except ImportError:
        return []

    scan_dir = _ensureScanData()
    path = scan_dir / "finance.parquet"
    if not path.exists():
        return []

    try:
        lf = pl.scan_parquet(str(path))
        needed = ["stockCode", "bsns_year", "sj_div", "account_nm", "thstrm_amount", "fs_nm", "reprt_nm"]
        avail = lf.collect_schema().names()
        cols = [c for c in needed if c in avail]
        snap = (
            lf.select(cols)
            .filter(pl.col("fs_nm").str.contains("연결"))
            .filter(pl.col("reprt_nm").str.contains("4분기"))
            .collect()
        )
    except (pl.exceptions.PolarsError, OSError):
        return []
    if snap.is_empty():
        return []

    years = sorted(snap["bsns_year"].unique().to_list(), reverse=True)
    if not years:
        return []
    cur = snap.filter(pl.col("bsns_year") == years[0])

    # 섹터 β 는 sectorParams 에서 조회 (없으면 1.0)
    sector_beta = _sectorBetaFallback(sector)

    # peer 추출: cur 의 모든 종목 (섹터 매핑 테이블 없으므로 일단 무작위 샘플)
    # 향후: c.sector.industryGroup 기반 필터 개선
    all_codes = cur["stockCode"].unique().to_list()
    rng = random.Random(hash(sector) & 0xFFFFFFFF)
    rng.shuffle(all_codes)

    debt_nms = ["부채총계"]
    equity_nms = ["자본총계"]

    def _extract(df: pl.DataFrame, nms: list[str]) -> float | None:
        for nm in nms:
            r = df.filter(pl.col("account_nm") == nm)
            if not r.is_empty():
                return parseNumStr(r["thstrm_amount"][0])
        return None

    peers: list[dict[str, Any]] = []
    for sc in all_codes:
        if len(peers) >= limit:
            break
        stock = cur.filter(pl.col("stockCode") == sc)
        if stock.is_empty():
            continue
        debt = _extract(stock, debt_nms)
        eq = _extract(stock, equity_nms)
        if not debt or not eq or eq <= 0:
            continue
        de = debt / eq
        if de > 5.0 or de < 0:  # 자본잠식/극단값 제외
            continue
        peers.append(
            {
                "code": sc,
                "betaLevered": sector_beta,  # 섹터 β (수익률 회귀 미구현 — 향후 개선)
                "de": round(de, 3),
            }
        )

    return peers


def _sectorBetaFallback(sector: str) -> float:
    """sectorParams 에서 섹터 β 조회. 없으면 1.0."""
    from dartlab.core.sector import getSectorParamsByName

    try:
        sp = getSectorParamsByName(sector)
        if sp and hasattr(sp, "beta") and sp.beta:
            return float(sp.beta)
    except (AttributeError, ValueError, TypeError):
        pass
    return 1.0
