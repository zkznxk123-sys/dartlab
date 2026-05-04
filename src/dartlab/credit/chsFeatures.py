"""Company → CHS feature 추출 SSOT.

L0 공용 유틸. credit engine 과 valuation survival 이 동일 경로로 CHS 부도확률을
계산할 수 있도록 feature 추출 로직을 한 곳에 보관.

credit/engine.py::_calcCHSAdjustment 에서 분리 — 순환 의존 방지.
"""

from __future__ import annotations

from typing import Any

from dartlab.credit.chsModel import CHSResult, calcCHS


def extractChsFeatures(company: Any) -> dict | None:
    """company 객체 → CHS 입력 dict.

    Returns
    -------
    dict | None
        netIncome, totalLiabilities, cash, totalAssets, marketCap,
        equityVolatility, excessReturn, stockPrice 키.
        입력 부족 시 None.
    """
    try:
        from dartlab.core.utils.helpers import toDictBySnakeId
    except ImportError:
        return None

    # 재무 추출
    try:
        bs = company.select("BS", ["자산총계", "부채총계", "현금및현금성자산"])
        income = company.select("IS", ["당기순이익"])
        bs_parsed = toDictBySnakeId(bs)
        is_parsed = toDictBySnakeId(income)
        if not bs_parsed or not is_parsed:
            return None
        bs_data, bs_periods = bs_parsed
        is_data, _ = is_parsed
        if not bs_periods:
            return None
        latest = bs_periods[0]

        def _bs(*keys: str) -> float | None:
            for k in keys:
                v = (bs_data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return None

        def _is(*keys: str) -> float | None:
            for k in keys:
                v = (is_data.get(k) or {}).get(latest)
                if v:
                    return float(v)
            return None

        ta = _bs("total_assets", "자산총계")
        tl = _bs("total_liabilities", "부채총계")
        cash = _bs("cash_and_cash_equivalents", "cash_and_equivalents")
        ni = _is("net_profit", "net_income", "당기순이익")
    except (AttributeError, KeyError, TypeError, ValueError):
        return None

    if any(v is None for v in (ta, tl, cash, ni)):
        return None

    # 주가 수집 (시가총액, 변동성, excessReturn)
    market_cap, sigma, exret, stock_price = _gatherMarketData(company)
    if market_cap is None:
        return None

    return {
        "netIncome": ni,
        "totalLiabilities": tl,
        "cash": cash,
        "totalAssets": ta,
        "marketCap": market_cap,
        "equityVolatility": sigma,
        "excessReturn": exret,
        "stockPrice": stock_price,
    }


def computeChsProbability(company: Any) -> dict | None:
    """company → CHS 부도확률 + zone.

    Returns
    -------
    dict | None
        probability : float — 12M 부도확률
        zone : str — "safe"/"watch"/"distress"
        features : dict — 입력 feature (디버깅)
    """
    features = extractChsFeatures(company)
    if not features:
        return None

    result: CHSResult | None = calcCHS(**features)
    if not isinstance(result, CHSResult):
        return None

    return {
        "probability": result.probability,
        "zone": result.zone,
        "logitScore": result.logitScore,
        "features": features,
    }


def _gatherMarketData(company: Any) -> tuple[float | None, float | None, float | None, float | None]:
    """주가 시계열에서 시가총액 / 변동성 / excessReturn / 주가 추출."""
    try:
        import dartlab

        code = getattr(company, "stockCode", None)
        if not code:
            return None, None, None, None
        price_df = dartlab.gather("price", code)
        if price_df is None or not hasattr(price_df, "height") or price_df.height < 30:
            return None, None, None, None
        closes = [float(c) for c in price_df["close"].to_list() if c is not None]
        if len(closes) < 30:
            return None, None, None, None
        latest_price = closes[-1]
        # 변동성 — 연환산 일별 수익률 표준편차
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1]]
        if len(returns) < 10:
            return None, None, None, latest_price
        mean_r = sum(returns) / len(returns)
        var_r = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        sigma = (var_r**0.5) * (252**0.5)
        exret = (closes[-1] / closes[0] - 1) if closes[0] else 0.0

        # 주식수는 calcDcf 역산 또는 BS 시도 — 여기서는 proxy
        shares = _estimateShares(company, latest_price)
        market_cap = shares * latest_price if shares else None
        return market_cap, sigma, exret, latest_price
    except (ImportError, AttributeError, KeyError, TypeError, ValueError, IndexError):
        return None, None, None, None


def _estimateShares(company: Any, price: float) -> int | None:
    """주식수 역산 — calcDcf 결과의 equityValue / perShareValue."""
    try:
        from dartlab.analysis.financial.valuation import calcDcf

        r = calcDcf(company)
        if isinstance(r, dict):
            eq = r.get("equityValue")
            ps = r.get("perShareValue")
            if eq and ps and ps > 0:
                return int(eq / ps)
    except (ImportError, AttributeError, ValueError, TypeError):
        pass
    return None
