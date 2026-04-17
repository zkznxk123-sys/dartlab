"""Implied Equity Risk Premium — Damodaran 역산.

Gordon growth model 기반:
    ImpliedERP ≈ (E/P) × payout + g − Rf
    = dividend yield + buyback yield + sustainable growth − Rf

매 분기 시장 내재 프리미엄을 역산. historical ERP 대신 현재 시장 상태 반영.

근거: Damodaran, *Equity Risk Premiums: Determinants, Estimates and Implications* (annual).
https://pages.stern.nyu.edu/~adamodar/pc/datasets/histimpl.html
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

_CACHE_ROOT = Path("data/cache/impliedERP")


def calcImpliedERP(
    country: str = "KR",
    *,
    asOfDate: str | None = None,
    useCache: bool = True,
) -> dict[str, Any]:
    """Damodaran Implied ERP 역산 — Gordon 공식.

    Parameters
    ----------
    country : "KR" | "US" | ...
    asOfDate : ISO date. None 이면 현재 분기.
    useCache : 분기 cache 사용 여부 (최대 90일 이내).

    Returns
    -------
    dict — riskPremiums.loadDamodaranERP 와 **동일 키 셋**:
        countryCode, name, matureMarketERP, countryRiskPremium, totalERP,
        riskFreeRate, marginalTaxRate, rating, source, asOfDate
    추가 서브키:
        impliedERP, indexLevel, aggregateE, aggregateD, buybackYield,
        payoutRatio, method, sampleCount
    """
    from dartlab.core.finance.riskPremiums import loadDamodaranERP

    fallback = loadDamodaranERP(countryCode=country)

    # 분기 cache 체크
    quarter_key = _quarterKey(asOfDate)
    if useCache:
        cached = _loadCache(country, quarter_key)
        if cached is not None:
            return cached

    # 역산 시도
    try:
        computed = _computeImpliedERP(country, fallback)
    except (ImportError, OSError, ValueError, TypeError, KeyError):
        computed = None

    if computed is None:
        # fallback_historical 그대로 반환 (동일 스키마)
        fallback["source"] = "fallback_historical"
        fallback["impliedERP"] = None
        fallback["method"] = "none"
        fallback["sampleCount"] = 0
        return fallback

    # 성공 시 cache 저장
    if useCache:
        _saveCache(country, quarter_key, computed)

    return computed


def _computeImpliedERP(country: str, fallback: dict[str, Any]) -> dict[str, Any] | None:
    """실제 역산. 실패 시 None."""
    rf = float(fallback.get("riskFreeRate", 3.4))

    # 지수 심볼 매핑
    index_symbol = {"KR": "KOSPI", "US": "SPX"}.get(country)
    if not index_symbol:
        return None

    # 지수 레벨 수집
    index_level = _fetchIndexLevel(index_symbol)
    if index_level is None:
        return None

    # 전종목 aggregate (KR 만 — finance.parquet 의존)
    if country != "KR":
        # 다른 국가는 현재 aggregate 경로 미구현 → fallback
        return None

    totals = _aggregateFinanceSnapshot()
    if not totals:
        return None

    agg_ni = totals["netIncome"]
    agg_mc = totals["marketCapProxy"]  # 순자본 합산 (proxy)
    sample = totals["sampleCount"]

    if agg_ni <= 0 or agg_mc <= 0:
        return None

    # Earnings yield (aggregate NI / aggregate book equity proxy)
    earnings_yield = agg_ni / agg_mc  # 0.0~

    # Dividend yield — 최근 3Y CAGR of NI 를 g 로 사용 (임시)
    growth = totals.get("niGrowth", 0.02)
    growth = max(-0.02, min(growth, 0.08))  # 경계

    # 단순 Gordon: ERP ≈ E/P + g - Rf
    # 더 정교: ERP = D/P + g - Rf + retained × ROIC (Damodaran 2024)
    # 여기선 aggregate payout 없으면 간이 사용
    implied = (earnings_yield * 100) + (growth * 100) - rf
    implied = max(2.0, min(implied, 12.0))  # 경계

    total = implied
    mature = fallback.get("matureMarketERP", 4.6)
    crp = max(0.0, total - mature)

    return {
        "countryCode": country,
        "name": fallback.get("name", country),
        "matureMarketERP": mature,
        "countryRiskPremium": round(crp, 2),
        "totalERP": round(total, 2),
        "riskFreeRate": rf,
        "marginalTaxRate": fallback.get("marginalTaxRate", 24.2),
        "rating": fallback.get("rating", "Aa2"),
        "source": "implied_calc",
        "asOfDate": datetime.now().strftime("%Y-%m-%d"),
        # 서브키
        "impliedERP": round(implied, 2),
        "indexLevel": index_level,
        "aggregateE": agg_ni,
        "aggregateD": None,  # 배당 aggregate 미구현
        "buybackYield": None,
        "payoutRatio": None,
        "method": "gordon_simple",
        "sampleCount": sample,
    }


def _fetchIndexLevel(symbol: str) -> float | None:
    try:
        import dartlab

        df = dartlab.gather("price", symbol)
        if df is None or not hasattr(df, "height") or df.height < 1:
            return None
        closes = df["close"].to_list()
        for c in reversed(closes):
            if c is not None:
                return float(c)
    except (ImportError, AttributeError, KeyError, TypeError, ValueError):
        pass
    return None


def _aggregateFinanceSnapshot() -> dict[str, Any] | None:
    """scan/finance.parquet 전종목 순이익 + 자본 합산 (양수만).

    aggregate NI = Σ positive 순이익
    aggregate book = Σ positive 자본총계 (시가총액 proxy — 실 시총 데이터 없으므로)
    """
    try:
        import polars as pl

        from dartlab.scan._helpers import _ensureScanData, parse_num

        scan_dir = _ensureScanData()
        path = scan_dir / "finance.parquet"
        if not path.exists():
            return None

        lf = pl.scan_parquet(str(path))
        needed = [
            "stockCode",
            "bsns_year",
            "sj_div",
            "account_nm",
            "thstrm_amount",
            "frmtrm_amount",
            "fs_nm",
            "reprt_nm",
        ]
        avail = lf.collect_schema().names()
        cols = [c for c in needed if c in avail]
        snap = (
            lf.select(cols)
            .filter(pl.col("fs_nm").str.contains("연결"))
            .filter(pl.col("reprt_nm").str.contains("4분기"))
            .collect()
        )
        if snap.is_empty():
            return None

        years = sorted(snap["bsns_year"].unique().to_list(), reverse=True)
        if not years:
            return None
        year = years[0]
        cur = snap.filter(pl.col("bsns_year") == year)
        prev_year = years[1] if len(years) > 1 else None

        ni_nms = ["당기순이익", "당기순이익(손실)"]
        eq_nms = ["자본총계"]

        def _agg(df: pl.DataFrame, nms: list[str], field: str = "thstrm_amount") -> tuple[float, int]:
            total = 0.0
            count = 0
            for sc in df["stockCode"].unique().to_list():
                stock = df.filter(pl.col("stockCode") == sc)
                for nm in nms:
                    row = stock.filter(pl.col("account_nm") == nm)
                    if not row.is_empty():
                        v = parse_num(row[field][0])
                        if v is not None and v > 0:
                            total += v
                            count += 1
                        break
            return total, count

        ni_cur, sample = _agg(cur, ni_nms)
        eq_cur, _ = _agg(cur, eq_nms)

        growth = None
        if prev_year:
            prev = snap.filter(pl.col("bsns_year") == prev_year)
            ni_prev, _ = _agg(prev, ni_nms)
            if ni_prev > 0:
                growth = (ni_cur - ni_prev) / ni_prev

        return {
            "netIncome": ni_cur,
            "marketCapProxy": eq_cur,
            "niGrowth": growth if growth is not None else 0.02,
            "sampleCount": sample,
            "year": year,
        }
    except (ImportError, OSError, ValueError, TypeError, KeyError):
        return None


def _quarterKey(asOfDate: str | None) -> str:
    if asOfDate:
        d = datetime.fromisoformat(asOfDate)
    else:
        d = datetime.now()
    q = (d.month - 1) // 3 + 1
    return f"{d.year}Q{q}"


def _loadCache(country: str, quarter: str) -> dict[str, Any] | None:
    path = _CACHE_ROOT / f"{country}_{quarter}.json"
    if not path.exists():
        return None
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age_days = (datetime.now() - mtime).days
        if age_days > 90:
            return None
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        data["source"] = "cache_quarterly"
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _saveCache(country: str, quarter: str, data: dict[str, Any]) -> None:
    _CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    path = _CACHE_ROOT / f"{country}_{quarter}.json"
    try:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass
